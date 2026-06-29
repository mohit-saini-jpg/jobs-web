/**
 * ══════════════════════════════════════════════════════════════════════════
 *  TOP SARKARI JOBS — Universal Dynamic Rendering Engine (MERGED)
 *  File:    universal-renderer.js
 *  Version: 2026-06-01 (v4.0 — Single Renderer, Zero Patch Dependency)
 * ══════════════════════════════════════════════════════════════════════════
 *
 *  ARCHITECTURE
 *  ─────────────
 *  1. normalizeJob()   — Single normalization entry point for ALL JSON sources
 *  2. DeepParser       — Recursively walks ANY JSON structure
 *  3. CardBuilders     — Typed renderers (table, tags, grid, html, steps, FAQ)
 *  4. MasterInjector   — Ordered, dedup-safe section injection
 *  5. IntegrationHub   — Race-condition-free callback system
 *
 *  DESIGN PRINCIPLES (v4.0)
 *  ─────────────────────────
 *  ✅ ONE renderer — job-renderer-patch.js is fully merged and deleted
 *  ✅ ONE CSS class prefix (.udyn-*) — no .dyn-card, no .jp-dyn-* conflicts
 *  ✅ ONE normalizeJob() — all JSON source variations collapse here
 *  ✅ ALWAYS render every section — no conditional layout based on missing fields
 *  ✅ Data changes, NOT layout — same DOM structure for every job
 *  ✅ All DOM patching (apply mode, last date, links) lives in runBasePatches()
 *
 * ══════════════════════════════════════════════════════════════════════════
 */

(function () {
  'use strict';

  // Static pages are fully pre-rendered — skip JS renderer entirely
  if (window.__TSJ_RENDERER_DISABLED || window.__TSJ_STATIC_PAGE) return;

  /* ═══════════════════════════════════════════════════════════════════════
     § 1 — CSS (injected once, single .udyn-* namespace)
  ═══════════════════════════════════════════════════════════════════════ */
  const _CSS_ID = 'tsj-univ-v4-styles';
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
    .udyn-gen-table{width:100%;border-collapse:collapse;font-size:.82rem;min-width:280px}
    .udyn-gen-table th{width:36%;max-width:140px;background:#f8fafc;color:#374151;font-weight:700;padding:8px 12px;text-align:left;vertical-align:top;border-bottom:1px solid #e9eef4;word-break:break-word;white-space:normal}
    .udyn-gen-table td{padding:8px 12px;color:#1e293b;font-size:.83rem;line-height:1.65;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word;white-space:normal;overflow-wrap:break-word}
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
    /* ── Grid (fee, salary, physical) ── */
    .udyn-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr))}
    .udyn-grid-item{padding:10px 14px;border-right:1px solid #e9eef4;border-bottom:1px solid #e9eef4}
    .udyn-grid-label{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin-bottom:3px}
    .udyn-grid-val{font-size:.9rem;font-weight:700;color:#1e293b}
    .udyn-grid-note{padding:9px 14px;font-size:.81rem;color:#78350f;background:#fffbeb;border-top:1px solid #fde68a}
    /* ── FAQ accordion ── */
    .udyn-faq-item{border-bottom:1px solid #f1f5f9}
    .udyn-faq-item:last-child{border-bottom:none}
    /* FAQ */
    .udyn-faq-item{border-bottom:1px solid #e9edf4}
    .udyn-faq-item:last-child{border-bottom:none}
    .udyn-faq-q{display:flex;align-items:center;gap:10px;padding:12px 14px;font-size:.84rem;font-weight:600;color:#0f172a;cursor:pointer;background:#f8fafc;user-select:none;line-height:1.5;text-align:left}
    .udyn-faq-q:hover{background:#f0f7ff}
    .udyn-faq-num{flex-shrink:0;min-width:26px;height:26px;background:#4f46e5;color:#fff;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:800}
    .udyn-faq-qtext{flex:1;text-align:left;color:#1e293b;line-height:1.5}
    .udyn-faq-icon{color:#64748b;font-size:.75rem;flex-shrink:0;transition:transform .25s;margin-left:auto}
    .udyn-faq-q.open .udyn-faq-icon{transform:rotate(180deg);color:#4f46e5}
    .udyn-faq-a{display:none;padding:10px 14px 14px 50px;font-size:.83rem;color:#374151;line-height:1.75;background:#fff;border-top:1px solid #f1f5f9}
    .udyn-faq-a.open{display:block}
    @media(max-width:600px){
      .udyn-faq-q{padding:10px 10px;font-size:.8rem}
      .udyn-faq-a{padding:8px 10px 12px 10px;font-size:.8rem}
    }
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

    /* ══════════════════════════════════════════════
       FSCD LAYOUT STYLES (v1.0)
       Same design as FSCD.html — card grid layout
    ══════════════════════════════════════════════ */
    /* Hide old jp- cards when FSCD layout active */
    .fscd-active #layoutJob > .jp-card:not(#shortInfoCard),
    .fscd-active #layoutJob > .jp-main-cta,
    .fscd-active #layoutJob > .jp-tips-card { display:none!important; }

    /* Hero banner */
    .fscd-hero{background:linear-gradient(125deg,#0c4a6e 0%,#1a6b8a 100%);border-radius:1.4rem;padding:2rem 2.2rem;margin-bottom:1.6rem;color:#fff;position:relative;overflow:hidden;}
    .fscd-hero::after{content:"📢";font-size:10rem;opacity:.06;position:absolute;bottom:-20px;right:-10px;pointer-events:none;}
    .fscd-hero-badge{background:rgba(255,255,255,.18);backdrop-filter:blur(6px);border-radius:60px;padding:.3rem 1rem;display:inline-block;font-size:.72rem;font-weight:600;margin-bottom:.9rem;letter-spacing:.04em;}
    .fscd-hero-title{font-size:1.5rem;font-weight:800;letter-spacing:-.02em;line-height:1.35;margin-bottom:.8rem;}
    .fscd-hero-stats{display:flex;flex-wrap:wrap;gap:.9rem;margin-top:1.2rem;}
    .fscd-stat-pill{background:rgba(255,255,255,.12);border-radius:60px;padding:.4rem 1rem;display:flex;align-items:center;gap:7px;font-weight:500;font-size:.82rem;}

    /* Short info block */
    .fscd-short-info{background:#eef4fa;border-left:5px solid #1e7e9f;padding:1rem 1.4rem;border-radius:1rem;margin-bottom:1.6rem;font-weight:500;color:#165e7c;font-size:.88rem;line-height:1.7;}

    /* Grid layouts */
    .fscd-grid-2{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1.4rem;margin-bottom:1.4rem;}
    .fscd-grid-3{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1.4rem;margin-bottom:1.4rem;}
    @media(max-width:500px){.fscd-grid-2,.fscd-grid-3{grid-template-columns:1fr;}}

    /* FSCD Card */
    .fscd-card{background:#fff;border-radius:1.4rem;box-shadow:0 8px 24px -8px rgba(0,0,0,.07),0 1px 1px rgba(0,0,0,.02);border:1px solid #e9f0f5;overflow:hidden;transition:transform .18s,box-shadow .18s;margin-bottom:0;}
    .fscd-card:hover{transform:translateY(-2px);box-shadow:0 18px 32px -10px rgba(0,0,0,.1);}
    .fscd-card-full{margin-bottom:1.4rem;}
    .fscd-card-head{padding:1rem 1.4rem .5rem;font-weight:700;font-size:1rem;display:flex;align-items:center;gap:9px;border-bottom:2px solid #eff3f8;color:#0f172a;}
    .fscd-card-head i{color:#1a6d8a;font-size:1rem;}
    .fscd-card-body{padding:.9rem 1.4rem 1.2rem;}

    /* Info rows inside cards */
    .fscd-info-row{display:flex;justify-content:space-between;align-items:baseline;padding:.62rem 0;border-bottom:1px dashed #e9edf2;gap:10px;}
    .fscd-info-row:last-child{border-bottom:none;}
    .fscd-lbl{font-weight:600;color:#2c4f6e;font-size:.82rem;flex-shrink:0;min-width:110px;}
    .fscd-val{font-weight:500;font-size:.84rem;text-align:right;color:#1e293b;word-break:break-word;}
    .fscd-val.red{color:#dc2626;font-weight:700;}
    .fscd-val.green{color:#16a34a;font-weight:700;}

    /* Soft badge */
    .fscd-badge{background:#e1f0f7;color:#0c6b8f;border-radius:40px;padding:.18rem .8rem;font-size:.72rem;font-weight:600;display:inline-block;}
    .fscd-badge.gr{background:#dcfce7;color:#15803d;}
    .fscd-badge.or{background:#ffedd5;color:#ea580c;}

    /* Vacancy table */
    .fscd-tbl-wrap{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;margin:.5rem 0;}
    .fscd-vac-tbl{width:100%;border-collapse:collapse;font-size:.83rem;min-width:400px;}
    .fscd-vac-tbl th{background:#f4fafe;padding:.82rem 1rem;font-weight:700;color:#1c5a78;border-bottom:2px solid #dee8f0;text-align:left;white-space:nowrap;}
    .fscd-vac-tbl td{padding:.78rem 1rem;border-bottom:1px solid #eef2f8;vertical-align:top;word-break:break-word;line-height:1.6;}
    .fscd-vac-tbl tbody tr:hover td{background:#fafdff;}
    .fscd-vac-tbl tbody tr:last-child td{border-bottom:none;}
    .fscd-scroll-hint{font-size:.68rem;color:#94a3b8;text-align:right;padding:3px 2px 0;display:flex;align-items:center;justify-content:flex-end;gap:4px;}

    /* Tags */
    .fscd-tags{display:flex;flex-wrap:wrap;gap:7px;}
    .fscd-tag{display:inline-flex;align-items:center;gap:6px;background:#f0f7ff;border:1px solid #bfdbfe;border-radius:8px;padding:6px 11px;font-size:.79rem;font-weight:600;color:#1e40af;}
    .fscd-tag i{font-size:.74rem;}

    /* Numbered steps */
    .fscd-steps{list-style:none;padding:0;margin:0;}
    .fscd-step{display:flex;align-items:flex-start;gap:11px;padding:.62rem 0;border-bottom:1px solid #f1f5f9;font-size:.83rem;color:#1e293b;line-height:1.65;}
    .fscd-step:last-child{border-bottom:none;}
    .fscd-step-n{flex-shrink:0;width:23px;height:23px;background:#0f766e;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.68rem;font-weight:800;margin-top:2px;}
    .fscd-step i{color:#1d4ed8;flex-shrink:0;margin-top:3px;font-size:.78rem;}

    /* Instructions */
    .fscd-inst-list{list-style:none;padding:0;margin:0;}
    .fscd-inst{display:flex;align-items:flex-start;gap:9px;padding:.6rem 0;border-bottom:1px solid #f1f5f9;font-size:.83rem;color:#374151;line-height:1.65;}
    .fscd-inst:last-child{border-bottom:none;}
    .fscd-inst i{color:#ea580c;flex-shrink:0;margin-top:3px;font-size:.78rem;}

    /* FAQ */
    .fscd-faq-item{border-bottom:1px solid #eef2f8;padding-bottom:.75rem;margin-bottom:.75rem;}
    .fscd-faq-item:last-child{border-bottom:none;margin-bottom:0;}
    .fscd-faq-q{font-weight:700;display:flex;justify-content:space-between;align-items:flex-start;gap:8px;cursor:pointer;color:#134b66;font-size:.84rem;line-height:1.5;padding:.28rem 0;}
    .fscd-faq-q:hover{color:#0c5670;}
    .fscd-faq-q .fq-ico{flex-shrink:0;margin-top:3px;transition:transform .2s;font-size:.7rem;}
    .fscd-faq-a{margin-top:.4rem;color:#4a627a;font-size:.83rem;padding-left:.72rem;border-left:3px solid #9ac2d9;line-height:1.7;display:none;}
    .fscd-faq-a.open{display:block;}

    /* Icon link buttons */
    .fscd-icon-links{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:9px;}
    .fscd-ib{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;padding:11px 7px 9px;border-radius:11px;text-decoration:none;font-weight:700;font-size:.7rem;text-align:center;transition:.18s;min-height:74px;word-break:break-word;border:1px solid transparent;}
    .fscd-ib:hover{transform:translateY(-2px);box-shadow:0 4px 14px rgba(0,0,0,.11);}
    .fscd-ib-ico{width:40px;height:40px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:1rem;margin-bottom:2px;}
    .fscd-ib-lbl{font-size:.7rem;font-weight:700;line-height:1.3;color:inherit;}
    .fscd-ib-sub{font-size:.61rem;color:#64748b;font-weight:500;}
    .ib-gr{background:#f0fdf4;border-color:#bbf7d0;color:#15803d;} .ib-gr .fscd-ib-ico{background:#dcfce7;color:#16a34a;}
    .ib-bl{background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8;} .ib-bl .fscd-ib-ico{background:#dbeafe;color:#1d4ed8;}
    .ib-rd{background:#fff5f5;border-color:#fecaca;color:#dc2626;} .ib-rd .fscd-ib-ico{background:#fee2e2;color:#dc2626;}
    .ib-or{background:#fff7ed;border-color:#fed7aa;color:#ea580c;} .ib-or .fscd-ib-ico{background:#ffedd5;color:#ea580c;}
    .ib-pu{background:#faf5ff;border-color:#e9d5ff;color:#7c3aed;} .ib-pu .fscd-ib-ico{background:#ede9fe;color:#7c3aed;}
    .ib-te{background:#f0fdfa;border-color:#99f6e4;color:#0f766e;} .ib-te .fscd-ib-ico{background:#ccfbf1;color:#0f766e;}

    /* Links quick panel */
    .fscd-links-panel{background:#f9fdfe;border-radius:1.3rem;padding:1rem 1.4rem;margin:1rem 0 1.4rem;display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:11px;border:1px solid #e2edf5;box-shadow:0 2px 5px rgba(0,0,0,.02);}
    .fscd-lpanel-lbl{font-size:.87rem;font-weight:700;color:#165e7c;display:flex;align-items:center;gap:7px;}
    .fscd-lpanel-btns{display:flex;flex-wrap:wrap;gap:8px;}
    .fscd-lbtn{display:inline-flex;align-items:center;gap:7px;padding:.48rem 1.1rem;border-radius:60px;font-weight:600;font-size:.79rem;text-decoration:none;transition:.2s;border:none;}
    .fscd-lbtn.solid{background:#1a6d8a;color:#fff;} .fscd-lbtn.solid:hover{background:#0c5670;}
    .fscd-lbtn.green{background:#16a34a;color:#fff;} .fscd-lbtn.green:hover{background:#15803d;}
    .fscd-lbtn.outline{background:transparent;border:1px solid #cbdde9;color:#1a6d8a;} .fscd-lbtn.outline:hover{background:#eef4fa;}

    /* Responsive */
    @media(max-width:600px){
      .fscd-hero{padding:1.3rem 1.2rem;}
      .fscd-hero-title{font-size:1.1rem;}
      .fscd-card-head{font-size:.9rem;padding:.85rem 1rem .4rem;}
      .fscd-card-body{padding:.75rem 1rem 1rem;}
      .fscd-vac-tbl{font-size:.76rem;}
      .fscd-vac-tbl th,.fscd-vac-tbl td{padding:.65rem .7rem;}
      .fscd-icon-links{grid-template-columns:repeat(auto-fill,minmax(100px,1fr));}
      .fscd-ib{min-height:66px;padding:9px 5px 7px;}
      .fscd-ib-ico{width:34px;height:34px;font-size:.88rem;}
    }
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
      .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
      .replace(/_+/g,' ')
      .replace(/\s+/g,' ')
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

  function renderVal(v) {
    if (v == null) return '—';
    if (typeof v === 'object') return deepRender(v, 1);
    const s = String(v).trim();
    if (!s) return '—';
    if (isUrl(s)) return `<a href="${esc(s)}" target="_blank" rel="noopener" style="color:#1d4ed8;font-weight:600;word-break:break-all;">${esc(s)}</a>`;
    if (isHtml(s)) return s;
    return esc(s);
  }

  function fmtDate(val) {
    const s = safe(val);
    let m = s.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})$/);
    if (m) return `${m[3].padStart(2,'0')}/${m[2].padStart(2,'0')}/${m[1]}`;
    m = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
    if (m) return `${m[1].padStart(2,'0')}/${m[2].padStart(2,'0')}/${m[3]}`;
    return s;
  }

  function normUrl(raw) {
    const s = safe(raw);
    if (!s) return '';
    if (/^(https?:)?\/\//i.test(s) || /^(mailto:|tel:)/i.test(s)) return s;
    if (s[0] === '#' || s[0] === '?' || s[0] === '/') return s;
    if (s.indexOf('.html') !== -1 || s.slice(0,2) === './' || s.slice(0,3) === '../') return s;
    return 'https://' + s.replace(/^\/+/, '');
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 3 — FIELD NORMALIZER
     Single entry point — collapses ALL JSON source variations into ONE
     canonical structure. Handles: Complete_Jobs, merged_sarkari,
     dailyupdates, state-jobs, upcoming_jobs.
  ═══════════════════════════════════════════════════════════════════════ */

  function normalizeJob(raw) {
    if (!raw || typeof raw !== 'object') return raw;
    const job = Object.assign({}, raw);

    // ── FIX: Map sarkari_data camelCase keys → snake_case canonical ───
    // Master Complete_Jobs_Full_Data.json (SR_* / OFFLINE_FORM / *_JOBS /
    // ADMISSIONS records) uses camelCase. The rest of normalizeJob expects
    // snake_case. Alias them here so NO field is silently dropped.
    const _CAMEL_MAP = {
      importantDates:   'important_dates',
      applicationFee:   'application_fee',
      applicationFees:  'application_fees',
      importantLinks:   'important_links',
      shortInfo:        'short_information',
      shortInformation: 'short_information',
      postDate:         'post_date',
      lastDate:         'last_date',
      ageLimit:         'age_limit',
      vacancyDetails:   'vacancy_details',
      howToApply:       'how_to_apply',
      usefulLinks:      'useful_links',
      textSections:     'text_sections',
      nameOfPost:       'name_of_post',
      postName:         'post_name',
      organizationName: 'organization',
      totalVacancy:     'total_vacancy',
      totalVacancies:   'total_vacancy',
      salaryPayScale:   'salary',
    };
    for (const [cam, snk] of Object.entries(_CAMEL_MAP)) {
      if (hasContent(job[cam]) && !hasContent(job[snk])) job[snk] = job[cam];
    }
    // additionalData.howToApply → how_to_apply (master nests it)
    if (job.additionalData && typeof job.additionalData === 'object') {
      const adx = job.additionalData;
      if (!hasContent(job.how_to_apply) && hasContent(adx.howToApply)) job.how_to_apply = adx.howToApply;
      for (const [k, v] of Object.entries(adx)) {
        const sk = k.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();
        if (!hasContent(job[sk]) && hasContent(v)) job[sk] = v;
      }
    }
    // important_dates inner camelCase keys → snake_case (applicationBegin etc.)
    if (job.important_dates && typeof job.important_dates === 'object' && !Array.isArray(job.important_dates)) {
      const _id = job.important_dates, _out = {};
      for (const [k, v] of Object.entries(_id)) {
        const sk = k.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();
        if (!(sk in _out)) _out[sk] = v;   // replace camel key; first writer wins
      }
      job.important_dates = _out;
    }
    // application_fee inner camelCase keys → snake_case
    if (job.application_fee && typeof job.application_fee === 'object' && !Array.isArray(job.application_fee)) {
      const _fe = job.application_fee, _fout = {};
      for (const [k, v] of Object.entries(_fe)) {
        const sk = k.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();
        if (!(sk in _fout)) _fout[sk] = v;
      }
      job.application_fee = _fout;
    }

    // ── FIX: Build important_dates from FLAT fields ──────────────────
    // STATE_JOBS / UPCOMING_JOBS / CENTRAL_JOBS / ADMISSIONS records keep
    // dates as top-level fields (last_date, application_start, exam_date…)
    // with NO important_dates object. Assemble one so exDates() renders them.
    if (!hasContent(job.important_dates)) {
      const _FLAT_DATES = ['application_start','application_begin','notification_date',
        'last_date','fee_payment_last_date','exam_date','written_exam_date',
        'admit_card_date','interview_date','result_date','counselling_date','joining_date'];
      const _idAsm = {};
      for (const f of _FLAT_DATES) {
        if (hasContent(job[f])) _idAsm[f] = job[f];
      }
      if (Object.keys(_idAsm).length) job.important_dates = _idAsm;
    }

    // ── FIX: Build application_fee from FLAT fee_* fields ────────────
    if (!hasContent(job.application_fee)) {
      const _FEE_FLAT = {
        fee_general: 'general', fee_ur: 'ur', fee_obc: 'obc', fee_ews: 'ews',
        fee_sc: 'sc', fee_st: 'st', fee_sc_st: 'sc_st', fee_female: 'female',
        fee_ph: 'ph', fee_pwd: 'pwd', fee_general_obc: 'general_obc',
        fee_all: 'all',
      };
      const _feeAsm = {};
      for (const [flat, canon] of Object.entries(_FEE_FLAT)) {
        if (hasContent(job[flat])) _feeAsm[canon] = job[flat];
      }
      if (hasContent(job.fee_payment_mode)) _feeAsm.payment_mode = job.fee_payment_mode;
      if (Object.keys(_feeAsm).length) job.application_fee = _feeAsm;
    }

    // ── Unwrap state-jobs nested 'detail' object ──────────────────────
    if (job.detail && typeof job.detail === 'object') {
      const d = job.detail;
      for (const [k, v] of Object.entries(d)) {
        if (!hasContent(job[k]) && hasContent(v)) job[k] = v;
      }
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

    // FIX-6: Clean short_information — remove social media nav junk injected by scraper
    if (job.short_information) {
      job.short_information = job.short_information
        // Remove "Telegram Join Us WhatsApp Join Us Instagram Follow X Follow" nav text
        .replace(/telegram\s+join\s+us\s+whatsapp\s+join\s+us\s+instagram\s+follow\s+(x|twitter)\s+follow/gi, '')
        // Remove "SarkariResult® : SarkariResult.Com Official Since : 201..." branding
        .replace(/sarkari\s*result[®@]?\s*[:–-]?\s*sarkariresult\.com\s+official\s+since\s*:\s*\d*/gi, '')
        // Remove "Download the SarkariResult® Mobile App..." promo text
        .replace(/download\s+the\s+sarkari\s*result[®]?\s+mobile\s+app[^.]*\./gi, '')
        // Remove "Advt No.: CRPD/APPR/..." reference numbers at end (already in title)
        .replace(/\s*sbi\s+advt\s+no\.\s*:\s*[A-Z0-9\/\-]+\s*:/gi, ' ')
        // Remove trailing "Short Details of Notification" (always in title)
        .replace(/\s*short\s+details\s+of\s+notification\s*$/gi, '')
        .replace(/\s{2,}/g, ' ')
        .trim();
    }

    // ── Normalize important_dates keys ───────────────────────────────
    const id = job.important_dates || {};
    if (typeof id === 'object') {
      // Consolidate all "start" aliases → application_begin (canonical)
      id.application_begin = id.application_begin || id.application_start || id.application_start_date || id.start_date || id.starting_date || id.starting_date_online || '';
      // Consolidate all "last date" aliases → last_date (canonical)
      id.last_date = id.last_date || id.last_date_to_apply || id.application_last_date || id.closing_date || id.last_apply_date || '';
      id.exam_date = id.exam_date || job.exam_date || '';
      job.important_dates = id;
    }

    // ── Normalize application_fees → application_fee ─────────────────
    if (!hasContent(job.application_fee) && hasContent(job.application_fees)) {
      job.application_fee = job.application_fees;
    }

    // ── Collect ALL URLs from flat link fields ────────────────────────
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

    if (!job._udyn_links) job._udyn_links = [];

    for (const [field, meta] of Object.entries(MERGED_LINK_MAP)) {
      const url = safe(job[field]);
      if (isUrl(url)) {
        job._udyn_links.push({ label: meta.label, url, type: meta.type });
      }
    }

    // ── Parse important_links dict ────────────────────────────────────
    const il = job.important_links;
    const _jobTitle = safe(job.title || (job.basic_details && (job.basic_details.job_title || job.basic_details.post_name)) || '');
    const _orgName  = safe(job.organization || (job.basic_details && (job.basic_details.organization_name || job.basic_details.department)) || '');
    if (il && typeof il === 'object' && !Array.isArray(il)) {
      const _labels = (il._labels && typeof il._labels === 'object') ? il._labels : {};
      for (const [k, v] of Object.entries(il)) {
        if (k === '_labels' || k === 'seo_tags' || k === 'structured_links') continue;
        const urls = Array.isArray(v) ? v : [v];
        for (const url of urls) {
          const u = safe(url);
          if (!isUrl(u)) continue;
          const type = classifyLinkKey(k, u);
          // Prefer _labels[k] if available and not generic
          const labelOverride = safe((_labels[k] || ''));
          let label;
          if (labelOverride && !isGenericLabel(labelOverride)) {
            label = labelOverride;
          } else {
            const rawLabel = smartLinkLabel(k, u, urls.length > 1 ? urls.indexOf(url) + 1 : 0, `${_jobTitle} ${_orgName}`.trim());
            label = isGenericLabel(rawLabel) ? generateSeoAnchor(u, type, _jobTitle, _orgName) : rawLabel;
          }
          job._udyn_links.push({ label, url: u, type });
        }
      }
    } else if (Array.isArray(il)) {
      for (const item of il) {
        if (typeof item === 'string' && isUrl(item)) {
          const type = classifyLinkKey('link', item);
          const rawLabel = smartLinkLabel('link', item, 0);
          const label = isGenericLabel(rawLabel) ? generateSeoAnchor(item, type, _jobTitle, _orgName) : rawLabel;
          job._udyn_links.push({ label, url: item, type });
        } else if (item && typeof item === 'object') {
          const url = safe(item.url || item.link || item.href || '');
          const rawLabel = safe(item.label || item.text || item.name || item.title || '');
          if (isUrl(url)) {
            const type = classifyLinkKey(rawLabel || 'link', url);
            const label = isGenericLabel(rawLabel) ? generateSeoAnchor(url, type, _jobTitle, _orgName) : rawLabel;
            job._udyn_links.push({ label, url, type });
          }
        }
      }
    }

    // ── Parse useful_links ────────────────────────────────────────────
    if (job.useful_links) {
      if (Array.isArray(job.useful_links)) {
        for (const item of job.useful_links) {
          if (!item) continue;
          const rawLabel = safe(item.title || item.name || item.label || '');
          const rawLinks = item.links || item.link || item.url || '';
          const urls = Array.isArray(rawLinks) ? rawLinks : [rawLinks];
          urls.forEach((u, idx) => {
            const url = safe(u);
            if (!isUrl(url)) return;
            if (/youtu\.?be|youtube\.com/i.test(url)) return;
            const type = classifyLinkKey(rawLabel || 'link', url);
            let finalLabel;
            if (urls.length > 1) {
              finalLabel = isGenericLabel(rawLabel) ? generateSeoAnchor(url, type, _jobTitle, _orgName) : `${rawLabel} (${idx + 1})`;
            } else {
              finalLabel = isGenericLabel(rawLabel) ? generateSeoAnchor(url, type, _jobTitle, _orgName) : rawLabel;
            }
            job._udyn_links.push({ label: finalLabel, url, type });
          });
        }
      } else if (typeof job.useful_links === 'object') {
        // FIX-5: useful_links is dict — skip '_all' key (it duplicates top-level links already collected)
        // Process only flat key→url pairs
        for (const [k, v] of Object.entries(job.useful_links)) {
          if (k === '_all' || k.startsWith('_')) continue; // _all causes duplicate links
          if (typeof v === 'string' && isUrl(v)) {
            const type = classifyLinkKey(k, v);
            const rawLabel = smartLinkLabel(k, v, 0);
            const label = isGenericLabel(rawLabel) ? generateSeoAnchor(v, type, _jobTitle, _orgName) : rawLabel;
            job._udyn_links.push({ label, url: v, type });
          } else if (Array.isArray(v)) {
            v.forEach((item, idx) => {
              if (item && typeof item === 'object') {
                const url = safe(item.links || item.url || item.link || '');
                const lbl = safe(item.title || item.name || '');
                if (isUrl(url)) {
                  const type = classifyLinkKey(lbl || k, url);
                  const finalLbl = isGenericLabel(lbl) ? generateSeoAnchor(url, type, _jobTitle, _orgName) : (lbl || generateSeoAnchor(url, type, _jobTitle, _orgName));
                  job._udyn_links.push({ label: finalLbl, url, type });
                }
              }
            });
          }
        }
      }
    }

    // ── Deduplicate links ─────────────────────────────────────────────
    const seen = new Set();
    job._udyn_links = job._udyn_links.filter(l => {
      if (seen.has(l.url)) return false;
      seen.add(l.url);
      return true;
    });

    // ── Final SEO sanitization — replace any remaining generic labels ──
    job._udyn_links = job._udyn_links.map(l => {
      if (isGenericLabel(l.label)) {
        return { ...l, label: generateSeoAnchor(l.url, l.type, _jobTitle, _orgName) };
      }
      return l;
    });

    return job;
  }

  function classifyLinkKey(key, url) {
    const k = safe(key).toLowerCase();
    const u = safe(url).toLowerCase();
    if (/apply|register|registration|form|apply_online/i.test(k)) return 'apply';
    if (/login/i.test(k)) return 'login';
    if (/notification|advt|advertisement|pdf|syllabus|admit|result/i.test(k)) return 'pdf';
    if (/official|website|home/i.test(k)) return 'website';
    if (/video|youtube|youtu\.be|watch/i.test(k) || /youtu\.?be|youtube/i.test(u)) return 'video';
    if (isPdf(u)) return 'pdf';
    if (/youtu\.?be|youtube/i.test(u)) return 'video';
    if (/login|apply|register|form|candidate|exam\.aspx|online/i.test(u)) return 'apply';
    return 'default';
  }

  function smartLinkLabel(key, url, index, ctx) {
    // ctx = job title / org for SEO labels
    var c = (ctx || '').trim();
    if (/notification_pdf|official_notif/i.test(key)) return c ? `Download ${c} Notification PDF` : 'Official Notification PDF';
    if (/login/i.test(key)) return c ? `${c} Candidate Login` : 'Candidate Login';
    if (/click_here/i.test(key)) {
      if (/admit|hallticket/i.test(url)) return c ? `Download ${c} Admit Card` : 'Download Admit Card';
      if (/answer|anskey/i.test(url)) return c ? `${c} Answer Key` : 'Download Answer Key';
      if (/syllabus/i.test(url)) return c ? `Download ${c} Syllabus` : 'Download Syllabus';
      if (/result|merit|scorecard/i.test(url)) return c ? `Check ${c} Result` : 'Check Result';
      if (/login|candidate/i.test(url)) return c ? `${c} Candidate Login` : 'Candidate Login';
      if (isPdf(url)||/notification|advt|advertisement/i.test(url)) return c ? `Download ${c} Notification PDF` : 'Download Notification PDF';
      if (/register|signup/i.test(url)) return c ? `Register for ${c}` : 'Register Now';
      if (/apply|career|recruit|applic/i.test(url)) return c ? `Apply Online for ${c}` : 'Apply Online';
      if (index > 1) return `Official Link ${index}`;
      return c ? `${c} – Official Link` : 'Apply / Official Link';
    }
    if (/apply/i.test(key)) return c ? `Apply Online for ${c}` : 'Apply Online';
    if (/official/i.test(key)) return c ? `${c} Official Website` : 'Official Website';
    if (/notification|advt|advertisement/i.test(key)) return c ? `Download ${c} Notification` : 'Official Notification';
    if (/pdf/i.test(key) || isPdf(url)) return c ? `Download ${c} PDF` : 'Download PDF';
    if (/website|home/i.test(key)) return 'Official Website';
    return keyToLabel(key);
  }

  /* ── SEO Anchor Helpers ─────────────────────────────────────────────── */
  const GENERIC_LABELS = /^(click\s*here|open|link|read\s*more|view|here|apply|visit|download|click|null|undefined|na|n\/a)$/i;

  function isGenericLabel(label) {
    if (!label || !label.trim()) return true;
    return GENERIC_LABELS.test(label.trim());
  }

  function generateSeoAnchor(url, type, jobTitle, orgName) {
    const u = safe(url).toLowerCase();
    const title = safe(jobTitle);
    const org   = safe(orgName);
    const ctx   = title || org;

    // Detect by URL patterns first (most reliable)
    if (/admit.?card|hallticket|hall.?ticket/i.test(u))
      return ctx ? `Download ${ctx} Admit Card` : 'Download Admit Card';
    if (/answer.?key/i.test(u))
      return ctx ? `${ctx} Answer Key` : 'Answer Key';
    if (/syllabus/i.test(u))
      return ctx ? `Download ${ctx} Syllabus` : 'Download Syllabus';
    if (/result/i.test(u))
      return ctx ? `${ctx} Result` : 'Check Result';
    if (/notif|advt|advertisement|notification/i.test(u) || isPdf(u))
      return org ? `Download ${org} Notification PDF` : (title ? `Download ${title} Notification PDF` : 'Download Notification PDF');
    if (/apply|register|registration|form|candidate|online/i.test(u))
      return title ? `Apply Online for ${title}` : (org ? `Apply Online – ${org}` : 'Apply Online');
    if (/login/i.test(u))
      return ctx ? `${ctx} Candidate Login` : 'Candidate Login';

    // Fall back to type-based with context
    if (type === 'apply')
      return title ? `Apply Online for ${title}` : (org ? `Apply Online – ${org}` : 'Apply Online');
    if (type === 'pdf')
      return org ? `Download ${org} Notification PDF` : (title ? `Download ${title} Notification PDF` : 'Download PDF');
    if (type === 'website')
      return org ? `Visit ${org} Official Website` : 'Visit Official Website';
    if (type === 'login')
      return ctx ? `${ctx} Candidate Login` : 'Candidate Login';

    // Generic fallback with context
    return ctx ? `${ctx} – Official Link` : 'Official Link';
  }

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
    // Canonical key order with ALL known aliases merged to one label
    const DATE_ALIAS = [
      { keys: ['application_begin','application_start','application_start_date','starting_date','start_date',
                'starting_date_online','आवेदन शुरू','date of commencement','opening of online registration of application'],
        label: 'Application Start Date', highlight: false },
      { keys: ['last_date','last_date_to_apply','application_last_date','closing_date','last_apply_date',
                'अंतिम तिथि','last date to apply','closing date'],
        label: 'Last Date to Apply', highlight: true },
      { keys: ['fee_payment_last_date','fee_last_date','payment_last_date'],
        label: 'Fee Payment Last Date', highlight: false },
      { keys: ['correction_last_date','correction_date','correction_window'],
        label: 'Correction Window Last Date', highlight: false },
      { keys: ['notification_date','date of notification','date of advertisement','notification released'],
        label: 'Notification / Advertisement Date', highlight: false },
      { keys: ['exam_date','परीक्षा तिथि','written/omr/online examination date',
                'tentative date for computer based test (cbt)','cbt_date','written_exam_date'],
        label: 'Exam / CBT Date', highlight: false },
      { keys: ['admit_card_date','admit_card','admit_card_release','hall_ticket'],
        label: 'Admit Card Available', highlight: false },
      { keys: ['result_date','result','merit_list_date'],
        label: 'Result Date', highlight: false },
      { keys: ['interview_date','interview','dv_date','document_verification','document verification date'],
        label: 'Interview / DV Date', highlight: false },
      { keys: ['cut‑off date for age, qualification & experience','cutoff_date','age_cutoff_date'],
        label: 'Age / Qualification Cut-off Date', highlight: false },
      { keys: ['counselling_date','counselling'],
        label: 'Counselling Date', highlight: false },
      { keys: ['joining_date','joining'],
        label: 'Joining Date', highlight: false },
    ];
    const rows = [];
    const usedKeys = new Set();
    for (const def of DATE_ALIAS) {
      let found = '';
      for (const k of def.keys) {
        // case-insensitive key lookup
        const matchKey = Object.keys(id).find(ik => ik.toLowerCase() === k.toLowerCase() || ik === k);
        if (matchKey && hasContent(id[matchKey])) { found = safe(id[matchKey]); usedKeys.add(matchKey); break; }
      }
      if (found) rows.push({ label: def.label, val: fmtDate(found), highlight: def.highlight });
    }
    // Render any remaining unmapped keys (handles future/unknown date keys)
    for (const [k, v] of Object.entries(id)) {
      if (usedKeys.has(k) || k === 'raw' || k === 'rawDate' || k === 'event' || !hasContent(v)) continue;
      const strVal = safe(typeof v === 'object' ? JSON.stringify(v) : String(v));
      if (!strVal) continue;
      rows.push({ label: keyToLabel(k), val: fmtDate(strVal), highlight: /last/i.test(k) });
    }
    const rawText = safe(id.raw || id.rawDate || '');
    return { rows, rawText };
  }

  function exFees(job) {
    // Support both application_fee (freejobalert format) and application_fees (sarkari format)
    const fee = job.application_fee || job.application_fees || {};
    const feeIsStr = typeof fee === 'string';
    const feeObj = (typeof fee === 'object' && !Array.isArray(fee)) ? fee : {};
    const FEE_MAP = [
      ['general','General / UR'],['ur','UR'],['obc','OBC'],['ews','EWS'],
      ['sc','SC'],['st','ST'],['sc_st','SC / ST'],['female','Female / Women'],
      ['ph','PH / PwD'],['pwd','PwD'],['divyang','Divyang'],
      ['general_obc','General / OBC'],['gen_obc','Gen / OBC'],
      ['general_obc_ews','General / OBC / EWS'],['gen_obc_ews','Gen / OBC / EWS'],
      ['ur_obc_ews','UR / OBC / EWS'],['all','All Candidates'],
      ['all_candidates','All Candidates'],
    ];
    const usedKeys = new Set(FEE_MAP.map(([k]) => k).concat(['note','payment_note','payment_mode']));
    const items = [];
    for (const [k, label] of FEE_MAP) {
      const v = safe(feeObj[k]);
      if (v) items.push({ label, val: v });
    }
    if (!items.length && feeIsStr) {
      const feeStr = safe(fee);
      if (feeStr) {
        const segRegex = /(.+?)\s*:\s*(?:Rs\.?\s*)?(\d[\d,]*\/-?|0\/-?|Nil|Free|Exempted|No Fee)/gi;
        let m;
        while ((m = segRegex.exec(feeStr)) !== null) {
          let label = m[1].replace(/^\s*\([^)]*\)\s*/, '').trim();
          if (label.length > 90) continue;
          if (/pay the|through|mode only|debit card|credit card|net banking|e.?challan/i.test(label)) continue;
          const val = m[2].trim();
          if (label && val) items.push({ label, val });
        }
        if (!items.length) items.push({ label: 'Application Fee', val: feeStr });
      }
    }
    if (!feeIsStr) {
      for (const [k, v] of Object.entries(feeObj)) {
        if (usedKeys.has(k) || !hasContent(v)) continue;
        items.push({ label: keyToLabel(k), val: safe(v) });
      }
    }
    let note = '';
    if (!feeIsStr) {
      note = safe(feeObj.note || feeObj.payment_note || feeObj.payment_mode || '');
    } else {
      const feeStr = safe(fee);
      const noteMatch = feeStr.match(/Pay (?:the )?(?:Examination|Exam) Fee[^.!]+[.!]?/i)
                     || feeStr.match(/Pay[^.]+(?:Net Banking|Debit Card|E.?Challan)[^.]*\.?/i);
      if (noteMatch) note = noteMatch[0].trim();
    }
    return { items, note };
  }

  function exVacancy(job) {
    let rows = [];
    const vd = job.vacancy_details;
    if (Array.isArray(vd) && vd.length) {
      rows = vd.filter(r => {
        if (!r || typeof r !== 'object') return false;
        // FIX-7: Skip junk rows injected by SarkariResult scraper:
        const pn = safe(r.post_name || '');
        // Skip rows that are just a timestamp like "04 June 2026 | 07:17 PM"
        if (/^\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}\s*\|/i.test(pn)) return false;
        // Skip rows that are just a number (total post only row with no post name)
        if (/^\d{3,5}$/.test(pn.trim()) && Object.keys(r).length <= 2) return false;
        // Skip "How to Fill Form (Video Hindi): Version I | Version II" rows
        if (/how.to.fill.form|version\s+(i|ii|1|2)/i.test(pn)) return false;
        // Skip header-only rows (post_name + col headers only — no actual vacancy numbers)
        const hasVacancyData = r.total_post || r.eligibility || r.col_1 || r.ur || r.sc || r.st || r.obc || r.ews;
        // A pure header row has col_1,col_2... but no total_post or eligibility
        if (r.col_1 && !r.total_post && !r.eligibility && !r.ur) return false;
        return true;
      });
    } else if (typeof vd === 'object' && vd !== null && !Array.isArray(vd)) {
      // Object-style vacancy_details — treat as single row array
      if (Object.keys(vd).length > 0) rows = [vd];
    }
    const cw = job.category_wise_vacancy;
    // Normalize category_wise_vacancy — can be object, array, or null
    let cwNorm = {};
    if (Array.isArray(cw) && cw.length) {
      // Array of objects — will be rendered as table separately in card
      cwNorm = cw; // pass through as array
    } else if (cw && typeof cw === 'object') {
      cwNorm = cw;
    }
    return { rows, cw: cwNorm };
  }

  function exSalary(job) {
    const sd = job.salary_details || {};
    // Priority: salary_details > salary > salary_pay_scale (root or basic_details)
    const flat = safe(
      job.salary ||
      job.salary_pay_scale ||
      (job.basic_details && (job.basic_details.salary || job.basic_details.salary_pay_scale)) ||
      ''
    );
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
    return job.selection_process || (job.basic_details && job.basic_details.selection_process) || [];
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

  function exQualification(job) {
    const q = job.qualification || {};
    const flat = safe(job.education_qualification || job.eligibility || '');
    if (typeof q === 'string') return q || flat || null;
    if (typeof q === 'object') {
      // Full object — return the whole object for deep rendering
      if (Object.keys(q).length > 0) {
        // Flatten matched_qualifications array into readable form
        const mq = q.matched_qualifications;
        if (Array.isArray(mq) && mq.length > 0 && Object.keys(q).length === 1) {
          // Only matched_qualifications present — show as tags with note
          return { matched_qualifications: mq };
        }
        return q;
      }
      return flat || null;
    }
    return flat || null;
  }

  function exTables(job) { return job.tables || null; }
  function exTextSections(job) { return job.text_sections || null; }

  const KNOWN_KEYS = new Set([
    'basic_details','important_dates','application_fee','application_fees',
    'age_limit','qualification','vacancy_details','category_wise_vacancy',
    'salary_details','selection_process','exam_pattern','syllabus',
    'physical_eligibility','physical_standards','how_to_apply','important_instructions',
    'important_links','important_links_obj','faq','faqs','seo_tags','category',
    'slug','title','post_name','organization','board_name','department',
    'total_vacancy','total_vacancies','total_post','apply_mode','application_mode','mode',
    'last_date','last_date_to_apply','application_begin','application_start','application_start_date',
    'exam_date','salary','salary_pay_scale','minimum_age','maximum_age','age_relaxation',
    'education_qualification','eligibility','experience_required',
    'short_information','jobs_info','source_url','apply_online',
    'official_website','official_website_link','form_pdf_free_link',
    'official_notification_pdf_link','apply_online_link','application_form_pdf_link',
    'form_pdf_link','listing_date','last_updated','apply_process',
    'post_date','status','useful_links','sequence','job_location','job_type',
    'homepage_serial','closing_date','application_last_date','instructions',
    'tables','sections','text_sections','id','name','url','date','lastDate','postDate',
    'board','detail','_udyn_links','state','items','scraper_errors','sync_stats',
    'generated_at','sources','total_records','freejobalert_categories','sarkari_data',
    'education_jobs','state_jobs','notification_number','fee_payment_last_date',
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
  ═══════════════════════════════════════════════════════════════════════ */

  function deepRender(value, depth) {
    depth = depth || 0;
    if (value == null || value === '') return '<span style="color:#94a3b8;">—</span>';
    if (typeof value === 'boolean') return value ? '<span style="color:#16a34a;font-weight:700;">Yes</span>' : '<span style="color:#dc2626;font-weight:700;">No</span>';
    if (typeof value === 'number') return `<strong>${value}</strong>`;
    if (typeof value === 'string') {
      const s = value.trim();
      if (!s) return '<span style="color:#94a3b8;">—</span>';
      if (isUrl(s)) {
        const t = isPdf(s) ? 'Download PDF' : (classifyLinkKey('link', s) === 'apply' ? 'Apply Online' : 'Open Link');
        return `<a href="${esc(s)}" target="_blank" rel="noopener" class="udyn-link-btn ${isPdf(s) ? 'udyn-link-pdf' : 'udyn-link-website'}" style="font-size:.78rem;padding:3px 10px;">${t}</a>`;
      }
      if (isHtml(s)) return `<div class="udyn-html-body" style="padding:0;">${s}</div>`;
      if (/\n/.test(s)) return textToHtml(s);
      return esc(s);
    }
    if (Array.isArray(value)) {
      if (!value.length) return '<span style="color:#94a3b8;">—</span>';
      if (value.every(x => typeof x === 'string' && isUrl(x))) {
        return value.map(u => `<a href="${esc(u)}" target="_blank" rel="noopener" class="udyn-link-btn ${isPdf(u) ? 'udyn-link-pdf' : 'udyn-link-apply'}" style="font-size:.78rem;padding:3px 10px;margin:2px 4px 2px 0;display:inline-flex;">${isPdf(u) ? 'Download PDF' : 'Apply Online'}</a>`).join('');
      }
      if (value.every(x => typeof x === 'string')) {
        return `<div class="udyn-tag-list" style="padding:0;">${value.map(s => `<div class="udyn-tag">${esc(s)}</div>`).join('')}</div>`;
      }
      if (value.every(x => x && typeof x === 'object' && !Array.isArray(x))) {
        return buildAoOTable(value);
      }
      return value.map(item => `<div style="margin-bottom:4px;">${deepRender(item, depth+1)}</div>`).join('');
    }
    if (typeof value === 'object') {
      const pairs = Object.entries(value).filter(([, v]) => hasContent(v));
      if (!pairs.length) return '<span style="color:#94a3b8;">—</span>';
      if (pairs.length === 1 && /^(details?|description|note|info|text|content)$/i.test(pairs[0][0])) {
        const txt = safe(String(pairs[0][1]));
        return `<div style="font-size:.88rem;color:#1e293b;line-height:1.85;">${esc(txt).replace(/\n/g,'<br>')}</div>`;
      }
      if (depth > 2) {
        return pairs.map(([k, v]) => `<strong>${esc(keyToLabel(k))}:</strong> ${deepRender(v, depth+1)}`).join('<br>');
      }
      const rows = pairs.map(([k, v]) =>
        `<tr><th>${esc(keyToLabel(k))}</th><td>${deepRender(v, depth+1)}</td></tr>`
      ).join('');
      return `<div class="udyn-table-scroll"><table class="udyn-gen-table">${rows}</table></div>`;
    }
    return esc(String(value));
  }

  function buildAoOTable(arr) {
    const cols = [...new Set(arr.flatMap(r => Object.keys(r)))];
    const thead = `<thead><tr>${cols.map(c => `<th>${esc(keyToLabel(c))}</th>`).join('')}</tr></thead>`;
    const tbody = arr.map(r =>
      `<tr>${cols.map(c => `<td>${deepRender(r[c], 1)}</td>`).join('')}</tr>`
    ).join('');
    return `<div class="udyn-table-scroll"><table class="udyn-vac-table">${thead}<tbody>${tbody}</tbody></table></div>`;
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 6 — CARD DOM BUILDERS (all use .udyn-card / .udyn-* classes)
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
    const isFree = v => /nil|^0\/?-?$|free|no fee|exempt/i.test(v.trim());
    if (items.length === 1 && items[0].val.length > 60) {
      const noteHtml = note ? `<div class="udyn-grid-note">${esc(note)}</div>` : '';
      return makeCard('udyn-fee','linear-gradient(135deg,#c2410c,#ea580c)',
        'fa-solid fa-indian-rupee-sign','Application Fee',
        `<div class="udyn-notice" style="padding:12px 14px;font-size:.83rem;color:#1e293b;line-height:1.75;white-space:pre-line;">${esc(items[0].val)}</div>${noteHtml}`);
    }
    const gridHtml = items.map(({ label, val }) =>
      `<div class="udyn-grid-item">` +
        `<div class="udyn-grid-label">${esc(label)}</div>` +
        `<div class="udyn-grid-val" style="${isFree(val) ? 'color:#16a34a;' : 'color:#1d4ed8;'}">${esc(val)}</div>` +
      `</div>`
    ).join('');
    const noteHtml = note ? `<div class="udyn-grid-note"><i class="fa-solid fa-circle-info" style="margin-right:5px;"></i>${esc(note)}</div>` : '';
    return makeCard('udyn-fee','linear-gradient(135deg,#c2410c,#ea580c)',
      'fa-solid fa-indian-rupee-sign','Application Fee',
      `<div class="udyn-grid" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr));">${gridHtml}</div>${noteHtml}`);
  }

  /* ── 6c. Vacancy Details ── */
  function cardVacancy(rows, cw) {
    let html = '';
    if (rows.length) {
      html = buildAoOTable(rows);
    }
    // category_wise_vacancy — array: render as second table; object: render as KV table
    if (hasContent(cw)) {
      let cwHtml = '';
      if (Array.isArray(cw) && cw.length) {
        cwHtml = `<div style="padding:7px 14px 3px;font-size:.79rem;font-weight:700;color:#1d4ed8;background:#f0f7ff;border-top:${html ? '1px solid #dbeafe' : 'none'};border-bottom:1px solid #dbeafe;">Category Wise Vacancy</div>${buildAoOTable(cw)}`;
      } else if (typeof cw === 'object') {
        const pairs = Object.entries(cw).filter(([, v]) => hasContent(v));
        if (pairs.length) {
          const tbody = pairs.map(([k, v]) => `<tr><td>${esc(keyToLabel(k))}</td><td>${esc(safe(v))}</td></tr>`).join('');
          cwHtml = `<div style="padding:7px 14px 3px;font-size:.79rem;font-weight:700;color:#1d4ed8;background:#f0f7ff;border-top:${html ? '1px solid #dbeafe' : 'none'};border-bottom:1px solid #dbeafe;">Category Wise Vacancy</div><div class="udyn-table-scroll"><table class="udyn-vac-table"><thead><tr><th>Category / Field</th><th>Value</th></tr></thead><tbody>${tbody}</tbody></table></div>`;
        }
      }
      if (cwHtml) html += cwHtml;
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
      if (pairs.length === 1 && /^(details?|description|note|info|text|content)$/i.test(pairs[0][0])) {
        const val = safe(pairs[0][1]);
        html = `<div style="padding:16px 20px;font-size:.9rem;color:#1e293b;line-height:1.85;word-break:break-word;">${esc(val).replace(/\n/g,'<br>')}</div>`;
      } else {
        const hasLongVal = pairs.some(([, v]) => safe(String(v)).length > 60);
        if (hasLongVal) {
          html = `<div class="udyn-table-scroll"><table class="udyn-gen-table">${pairs.map(([k, v]) =>
            `<tr><th style="width:30%;vertical-align:top;">${esc(keyToLabel(k))}</th>` +
            `<td style="line-height:1.7;">${deepRender(v, 1)}</td></tr>`
          ).join('')}</table>`;
        } else {
          html = `<div class="udyn-grid" style="grid-template-columns:repeat(auto-fill,minmax(180px,1fr));">${pairs.map(([k, v]) =>
            `<div class="udyn-grid-item"><div class="udyn-grid-label">${esc(keyToLabel(k))}</div><div class="udyn-grid-val">${deepRender(v, 1)}</div></div>`
          ).join('')}</div>`;
        }
      }
    } else if (typeof pe === 'string') {
      html = `<div style="padding:16px 20px;font-size:.9rem;color:#1e293b;line-height:1.85;">${esc(pe).replace(/\n/g,'<br>')}</div>`;
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
      // Detect if items contain table-like entries (e.g., "1 Subject 50 marks") vs step descriptions
      const knownSteps = ['Written Exam','CBT','Interview','Skill Test','Typing Test','Physical Test',
        'Medical Test','Document Verification','Merit List','Trade Test','Viva','Shortlisting','Driving Test','Practical Test'];
      const isStep = s => knownSteps.some(st => s.toLowerCase().includes(st.toLowerCase()));
      const stepItems = sp.filter(s => typeof s === 'string' && s.trim().length > 0);
      // Short step-name items → tags; longer descriptive items → numbered list
      const avg = stepItems.reduce((a,s) => a + s.length, 0) / (stepItems.length || 1);
      if (avg < 60 && stepItems.every(s => s.length < 120)) {
        html = `<div class="udyn-tag-list">${stepItems.map(s =>
          `<div class="udyn-tag"><i class="fa-solid fa-arrow-right-long"></i>${esc(s)}</div>`
        ).join('')}</div>`;
      } else {
        html = `<ul class="udyn-steps-list">${stepItems.map((s, i) =>
          `<li class="udyn-step"><span class="udyn-step-num">${i+1}</span><span>${esc(s)}</span></li>`
        ).join('')}</ul>`;
      }
    } else if (typeof sp === 'string' && sp.trim()) {
      const lines = sp.split(/\n+|\s*[,;]\s*(?=[A-Z])/).map(l => l.trim()).filter(Boolean);
      if (lines.length > 1 && lines.every(l => l.length < 100)) {
        html = `<div class="udyn-tag-list">${lines.map(s =>
          `<div class="udyn-tag"><i class="fa-solid fa-arrow-right-long"></i>${esc(s)}</div>`
        ).join('')}</div>`;
      } else {
        html = `<div class="udyn-detail" style="white-space:pre-line;">${esc(sp)}</div>`;
      }
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
    } else if (faqs && typeof faqs === 'object') {
      arr = Object.entries(faqs).map(function(e) { return { question: e[0], answer: e[1] }; });
    }
    if (!arr.length) return null;

    // FIX: Detect swapped Q/A (SarkariResult pattern — date in question, label in answer)
    arr = arr.map(function(f) {
      var q = safe(f.question || f.q || '');
      var a = safe(f.answer   || f.a || '');
      var ansIsLabel = /:\s*$/.test(a.trim()) ||
        /^(application|last date|exam date|admit card|fee|age|minimum|maximum|eligibility|vacancy|result|notification|start|end|begin|close)/i.test(a.trim());
      var qIsValue = /^\d{1,2}\/\d{1,2}\/\d{4}|^\d{2,4}$|^\d+\s*(years?|posts?|vacancies|rs\.?|rupees?|\/-)/i.test(q.trim());
      if (ansIsLabel && qIsValue) return { question: a.replace(/:\s*$/, '').trim(), answer: q };
      return f;
    });

    // Deduplicate — strip "Q1. " prefix before comparing
    var seenQ = {};
    arr = arr.filter(function(f) {
      var q = safe(f.question || f.q || '').toLowerCase().trim()
               .replace(/^q\d+[\.\)]\s*/i, '');  // strip "Q1. " prefix
      if (seenQ[q]) return false;
      seenQ[q] = true;
      return true;
    });

    // Build items — NO inline onclick (broken by HTML escaping)
    // Use data-faq-idx attribute + delegated event listener added after insert
    var html = arr.map(function(f, idx) {
      var q = safe(f.question || f.q || '');
      var rawAns = safe(f.answer || f.a || '');
      var aHtml = isHtml(rawAns) ? rawAns : esc(rawAns).replace(/\n/g, '<br>');
      return '<div class="udyn-faq-item">' +
        '<div class="udyn-faq-q" data-faq-idx="' + idx + '" role="button" tabindex="0">' +
          '<span class="udyn-faq-num">' + (idx + 1) + '</span>' +
          '<span class="udyn-faq-qtext">' + esc(q) + '</span>' +
          '<i class="fa-solid fa-chevron-down udyn-faq-icon"></i>' +
        '</div>' +
        '<div class="udyn-faq-a" id="faq-ans-' + idx + '">' + aHtml + '</div>' +
      '</div>';
    }).join('');

    var card = makeCard('udyn-faq', 'linear-gradient(135deg,#3730a3,#4f46e5)',
      'fa-solid fa-circle-question', 'FAQs', html);

    // Attach delegated click listener once card is created
    card.addEventListener('click', function(e) {
      var btn = e.target.closest('.udyn-faq-q');
      if (!btn) return;
      var ans = btn.nextElementSibling;
      if (!ans) return;
      var isOpen = ans.classList.contains('open');
      // Close all others in this card
      card.querySelectorAll('.udyn-faq-a.open').forEach(function(el) {
        el.classList.remove('open');
        var prevBtn = el.previousElementSibling;
        if (prevBtn) prevBtn.classList.remove('open');
      });
      // Toggle current
      if (!isOpen) {
        ans.classList.add('open');
        btn.classList.add('open');
      }
    });

    return card;
  }


  /* ── 6l. Jobs Info ── */
  function cardJobsInfo(htmlStr) {
    if (!htmlStr) return null;
    const text = stripHtml(htmlStr);
    if (text.length < 20) return null;
    const content = isHtml(htmlStr) ? `<div class="udyn-html-body">${htmlStr}</div>` : `<div class="udyn-detail">${textToHtml(htmlStr)}</div>`;
    return makeCard('udyn-jobs-info','linear-gradient(135deg,#0f766e,#0891b2)',
      'fa-solid fa-circle-info','About This Recruitment', content);
  }

  /* ── 6m. SR Tables ── */
  function renderTableRows(rows) {
    if (!Array.isArray(rows) || !rows.length) return '';
    const colCounts = {};
    for (const row of rows) {
      if (!Array.isArray(row) || row.length < 2) continue;
      colCounts[row.length] = (colCounts[row.length] || 0) + 1;
    }
    const colEntries = Object.entries(colCounts).sort((a, b) => b[1] - a[1]);
    const normalCols = colEntries.length ? parseInt(colEntries[0][0]) : 0;
    const totalRows = rows.filter(r => Array.isArray(r) && r.length >= 2).length;
    const cleanRows = rows.filter(row => {
      if (!Array.isArray(row)) return false;
      if (normalCols > 0 && totalRows > 1 && row.length > normalCols * 3) return false;
      return true;
    });
    const subTables = [];
    let cur = [], curCols = -1;
    for (const row of cleanRows) {
      if (!Array.isArray(row)) continue;
      if (row.length !== curCols) {
        if (cur.length) subTables.push(cur);
        cur = [row]; curCols = row.length;
      } else { cur.push(row); }
    }
    if (cur.length) subTables.push(cur);
    let html = '';
    for (const st of subTables) {
      if (!st.length) continue;
      const firstRow = st[0];
      const nextRow = st[1];
      const isHeader = nextRow &&
        firstRow.every(c => typeof c === 'string' && !isUrl(c) && c.length < 120) &&
        nextRow.length >= firstRow.length;
      const headerHtml = isHeader
        ? `<thead><tr>${firstRow.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>`
        : '';
      const dataRows = isHeader ? st.slice(1) : st;
      if (isHeader && dataRows.length === 0) continue;
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
        html += `<div class="udyn-table-scroll"><table class="udyn-gen-table" style="margin-bottom:0;">
          <tbody><tr><th>${esc(st[0][0])}</th><td>${esc(st[0][1])}</td></tr></tbody>
        </table></div>`;
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
      if (group && typeof group === 'object' && !Array.isArray(group)) {
        const tname = safe(group.table_name || '');
        const rows = group.rows;
        if (!Array.isArray(rows) || !rows.length) continue;
        const heading = tname
          ? `<div style="padding:9px 14px 5px;font-size:.8rem;font-weight:700;color:#1d4ed8;background:#f0f7ff;border-bottom:1px solid #dbeafe;line-height:1.4;">${esc(tname)}</div>`
          : '';
        const tableHtml = renderTableRows(rows);
        if (tableHtml) allHtml += `<div style="margin-bottom:2px;">${heading}${tableHtml}</div>`;
      } else if (Array.isArray(group) && group.length && Array.isArray(group[0])) {
        const tableHtml = renderTableRows(group);
        if (tableHtml) allHtml += tableHtml;
      }
    }
    if (!allHtml) return null;
    return makeCard('udyn-sr-tables','linear-gradient(135deg,#1d4ed8,#1d6dbc)',
      'fa-solid fa-table','Vacancy / Important Details', allHtml);
  }

  /* ── 6m2. Text Sections ── */
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
      const steps = content.split(/\s*\|\s*|\n+/).map(s => s.trim()).filter(Boolean);
      let bodyHtml = '';
      if (steps.length > 1) {
        bodyHtml = `<ul class="udyn-steps-list">${steps.map((s, i) =>
          `<li class="udyn-step"><span class="udyn-step-num">${i+1}</span><span>${esc(s)}</span></li>`
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

  /* ── 6n. Important Links ── */
  function cardLinks(links) {
    if (!links || !links.length) return null;
    const ORDER = { apply: 0, login: 1, pdf: 2, website: 3, default: 4 };
    const sorted = [...links].sort((a, b) => (ORDER[a.type] || 4) - (ORDER[b.type] || 4));
    const typeStyle = { apply: 'udyn-link-apply', login: 'udyn-link-login', pdf: 'udyn-link-pdf', website: 'udyn-link-website', video: 'udyn-link-video', default: 'udyn-link-default' };
    const typeLabel = { apply: 'Apply Now', login: 'Login', pdf: 'View PDF', website: 'Visit Website', video: 'Watch Video', default: 'Open Link' };
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

  /* ── 6o. Generic unknown field card ── */
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

    // FIX: isJunkAgeText — scraper sometimes puts navigation/social text in age_limit.raw
    function isJunkAgeText(s) {
      if (!s || s.length < 5) return true;
      // If it contains social media keywords or is clearly not age data
      if (/telegram|whatsapp|instagram|twitter|follow|join us|sarkari result|freejobalert|click here|official site|advt no\.|short details/i.test(s)) return true;
      // Raw field that has no digits at all — definitely junk
      if (!/\d/.test(s) && s.length > 30) return true;
      return false;
    }

    const minAge = safe(job.minimum_age || age.minimum_age || age.min_age || '');
    const maxAge = safe(job.maximum_age || age.maximum_age || age.max_age || age.age_limit || '');
    // age_details — may be a compact "18 to 45 years" or full paragraph
    const ageDet = safe(age.age_details || age.details || age.info || '');
    // FIX: age.raw is often junk scraped text — skip it unless it looks like real age data
    const rawAge = safe(age.raw || '');
    const relax  = safe(job.age_relaxation || age.age_relaxation || age.relaxation || '');
    const pairs  = [];
    if (minAge && !isJunkAgeText(minAge)) pairs.push(['Minimum Age', minAge, false]);
    if (maxAge && !isJunkAgeText(maxAge)) pairs.push(['Maximum / Upper Age Limit', maxAge, false]);
    // If age_details is short (looks like "18 to 45 years"), show as row; if long, use detail block
    const isLongDet = ageDet.length > 80;
    if (ageDet && !isJunkAgeText(ageDet) && !isLongDet) pairs.push(['Age Limit', ageDet, false]);
    if (relax && !isJunkAgeText(relax) && relax !== ageDet) pairs.push(['Age Relaxation', relax, relax.length > 80]);
    // FIX: Only show raw if it has useful age data and not junk
    if (rawAge && !isJunkAgeText(rawAge) && !minAge && !maxAge && !ageDet) {
      pairs.push(['Age Limit', rawAge, rawAge.length > 80]);
    }
    const KNOWN_AGE = new Set(['minimum_age','maximum_age','min_age','max_age','age_limit','age_details','age_relaxation','details','info','relaxation','raw']);
    for (const [k, v] of Object.entries(age)) {
      if (KNOWN_AGE.has(k) || !hasContent(v)) continue;
      const sv = safe(v);
      if (!isJunkAgeText(sv)) pairs.push([keyToLabel(k), sv, false]);
    }
    // If no real data found, show note from FAQ if available
    if (!pairs.length && !ageDet) {
      // Try to pull min/max from faq (SBI pattern: faq has Minimum Age / Maximum Age)
      const faqArr = job.faq || job.faqs || [];
      let faqMin = '', faqMax = '', faqRelax = '';
      for (const f of (Array.isArray(faqArr) ? faqArr : [])) {
        const ans = safe(f.answer || f.a || '').toLowerCase();
        const q   = safe(f.question || f.q || '');
        if (/minimum age/i.test(ans) && /^\d+/.test(q)) faqMin = q;
        if (/maximum age/i.test(ans) && /^\d+/.test(q)) faqMax = q;
        if (/age relaxation/i.test(ans)) faqRelax = q;
      }
      if (faqMin) pairs.push(['Minimum Age', faqMin, false]);
      if (faqMax) pairs.push(['Maximum Age', faqMax, false]);
      if (faqRelax) pairs.push(['Age Relaxation', faqRelax, false]);
    }
    if (!pairs.length) return null;
    let rowsHtml = pairs.filter(([,,long]) => !long)
      .map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('');
    // Long text values rendered as detail block below table
    let detailHtml = '';
    if (isLongDet && !isJunkAgeText(ageDet)) detailHtml += `<div class="udyn-detail" style="font-size:.82rem;line-height:1.8;color:#374151;white-space:pre-line;">${esc(ageDet)}</div>`;
    for (const [k, v, long] of pairs) {
      if (!long || !v) continue;
      detailHtml += `<div class="udyn-detail"><strong>${esc(k)}:</strong><br><span style="font-size:.82rem;line-height:1.8;color:#374151;white-space:pre-line;">${esc(v)}</span></div>`;
    }
    if (!rowsHtml && !detailHtml) return null;
    const tableHtml = rowsHtml
      ? `<div class="udyn-table-scroll"><table class="udyn-gen-table">${rowsHtml}</table></div>`
      : '';
    return makeCard('udyn-age-limit','linear-gradient(135deg,#7c3aed,#8b5cf6)',
      'fa-solid fa-user-clock','Age Limit Details',
      tableHtml + detailHtml);
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
    // Applies to all flat-schema categories that carry sections[]:
    // UPCOMING_JOBS / STATE_JOBS / CENTRAL_JOBS / ADMISSIONS
    const FLAT_CATS = ['UPCOMING_JOBS','STATE_JOBS','CENTRAL_JOBS','ADMISSIONS'];
    if (FLAT_CATS.indexOf(rawJob.category) === -1) return rawJob;
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
    // Capture any remaining section content (eligibility, notes, short details,
    // qualification text etc.) as text_sections so nothing is missed on the page.
    if (!rawJob.text_sections || !rawJob.text_sections.length) {
      const KNOWN = ['important dates','application fees','application fee','selection process'];
      const extra = [];
      for (const sec of sections) {
        const t = (sec.title || '').trim();
        if (t && KNOWN.indexOf(t.toLowerCase()) !== -1) continue;
        const lines = [];
        for (const blk of (sec.content || [])) {
          if (blk.type === 'paragraph' && blk.text) lines.push(blk.text);
          else if (blk.type === 'list' && Array.isArray(blk.items)) lines.push(...blk.items);
        }
        const content = lines.filter(Boolean).join('\n').trim();
        if (content) extra.push({ section: t || 'Details', content });
      }
      if (extra.length) rawJob.text_sections = extra;
    }
    return rawJob;
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 8 — DOM HELPERS
  ═══════════════════════════════════════════════════════════════════════ */

  function insertBeforeLinks(card) {
    const layout = document.getElementById('layoutJob');
    if (!layout) return;
    let linksCard = null;
    for (const c of layout.querySelectorAll('.jp-card, .udyn-card')) {
      const head = c.querySelector('.jp-sec-head, .udyn-head');
      if (head && /important links/i.test(head.textContent)) { linksCard = c; break; }
    }
    if (linksCard) layout.insertBefore(card, linksCard);
    else layout.appendChild(card);
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
     § 10 — DOM PATCHER
     Patches base-renderer DOM elements AND injects missing links.
     Merged from job-renderer-patch.js Section 8 (runAllPatches).
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
    /* ── Skip jp-card DOM shows if FSCD layout is active ── */
    const _fscdActive = !!(document.getElementById('fscd-main-portal'));
    const bd = rawJob.basic_details || {};
    const id = rawJob.important_dates || {};
    const age = rawJob.age_limit || {};

    // ── Organization ──────────────────────────────────────────────────
    const org = safe(rawJob.organization || rawJob.board_name || rawJob.department || bd.organization_name || bd.department || '');
    patchField('statOrg', org);
    patchTableRow('jbTable', /organisation/i, org);

    // ── Total vacancies ───────────────────────────────────────────────
    const tv = safe(rawJob.total_vacancy || rawJob.total_vacancies || bd.total_vacancies || rawJob.total_post || '');
    if (tv) { patchField('statPosts', tv); patchTableRow('jbTable', /total vacancies/i, tv); }

    // ── Apply Mode — ALWAYS overwrite from JSON ───────────────────────
    const mode = safe(rawJob.apply_mode || rawJob.application_mode || bd.apply_mode || bd.application_mode || '');
    if (mode) {
      const el = document.getElementById('statApplyMode');
      if (el) {
        el.textContent = mode;
        el.style.color = /offline/i.test(mode) ? '#ea580c' : '#16a34a';
      }
      patchTableRow('jbTable', /application mode/i, mode);
      // Highlights bar
      const hlItems = document.querySelectorAll('#hlList .jp-hl-item span');
      for (const span of hlItems) {
        if (/apply mode/i.test(span.textContent)) { span.textContent = 'Apply Mode: ' + mode; break; }
      }
    }

    // ── Last Date — ALWAYS overwrite from JSON ────────────────────────
    const lastDateRaw = safe(id.last_date || id.application_last_date || rawJob.last_date || rawJob.last_date_to_apply || '');
    if (lastDateRaw && !/^see notification$/i.test(lastDateRaw) && lastDateRaw !== '—') {
      const fmt = fmtDate(lastDateRaw);
      const statEl = document.getElementById('statLastDate');
      if (statEl) statEl.textContent = fmt;
      const sideVal = document.getElementById('dateLastVal');
      if (sideVal) sideVal.textContent = fmt;
      const sideRow = document.getElementById('dateLastRow');
      if (sideRow) sideRow.style.display = '';
      const metaWrap = document.getElementById('metaLastDateWrap');
      const metaEl = document.getElementById('metaLastDate');
      if (metaWrap && metaEl) { metaEl.textContent = 'Last Date: ' + fmt; metaWrap.style.display = ''; }
      // Overview table
      for (const tr of document.querySelectorAll('#jbTable tbody tr')) {
        const th = tr.querySelector('th');
        if (th && /last date/i.test(th.textContent)) {
          const td = tr.querySelector('td');
          if (td) { td.textContent = fmt; td.style.color = '#dc2626'; td.style.fontWeight = '800'; }
          break;
        }
      }
      // Highlights bar
      const hlItems = document.querySelectorAll('#hlList .jp-hl-item span');
      for (const span of hlItems) {
        if (/last date/i.test(span.textContent)) { span.textContent = '⚠ Last Date: ' + fmt; break; }
      }
    }

    // ── Salary in overview table ──────────────────────────────────────
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

    // ── Age card patch ────────────────────────────────────────────────
    const minAge = safe(rawJob.minimum_age || age.minimum_age || '');
    const maxAge = safe(rawJob.maximum_age || age.maximum_age || age.age_limit || age.age_details || '');
    const ageRelax = safe(rawJob.age_relaxation || age.age_relaxation || age.details || '');
    const ageCard = document.getElementById('ageCard');
    if (!_fscdActive && (minAge || maxAge || ageRelax) && ageCard && ageCard.style.display === 'none') {
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

    // ── Qualification card patch ──────────────────────────────────────
    const eduQual = safe(rawJob.education_qualification || rawJob.eligibility || (rawJob.qualification && (rawJob.qualification.education_qualification || rawJob.qualification.eligibility)) || '');
    const qualCard = document.getElementById('qualCard');
    if (!_fscdActive && eduQual && qualCard && qualCard.style.display === 'none') {
      qualCard.style.display = '';
      const qualContent = document.getElementById('qualContent');
      if (qualContent) qualContent.innerHTML = `<div class="jp-detail-text"><strong>Education Qualification:</strong> ${esc(eduQual)}</div>`;
    }

    // ── Short info patch ──────────────────────────────────────────────
    const shortInfo = safe(rawJob.short_information || rawJob.jobs_info || bd.short_information || '');
    const siCard = document.getElementById('shortInfoCard');
    const siText = document.getElementById('shortInfoText');
    if (!_fscdActive && shortInfo && siCard && siCard.style.display === 'none' && siText) {
      siCard.style.display = '';
      if (isHtml(shortInfo)) siText.innerHTML = shortInfo; else siText.textContent = shortInfo;
    }

    // ── Important Links — inject missing flat-field links ─────────────
    // (Merged from job-renderer-patch.js patchImportantLinks)
    const container = document.getElementById('linksActions');
    if (container) {
      const shown = new Set();
      for (const a of container.querySelectorAll('a[href]')) {
        const h = (a.getAttribute('href') || '').trim();
        if (h && h !== '#') shown.add(h);
      }
      const flatDefs = [
        { key: 'form_pdf_free_link',             label: 'Download Form (Free PDF)',  icon: 'fa-file-arrow-down', cls: 'jp-btn-orange', sub: 'Free PDF'     },
        { key: 'official_notification_pdf_link', label: 'Official Notification PDF', icon: 'fa-file-pdf',        cls: 'jp-btn-blue',   sub: 'Download PDF' },
        { key: 'official_website_link',          label: 'Official Website',          icon: 'fa-globe',           cls: 'jp-btn-red',    sub: 'Visit Now'    },
      ];
      let newHtml = '';
      for (const def of flatDefs) {
        const href = normUrl(safe(rawJob[def.key] || ''));
        if (!href || shown.has(href)) continue;
        shown.add(href);
        newHtml +=
          `<a href="${href}" target="_blank" rel="noopener" class="jp-btn ${def.cls}">` +
            `<span><i class="fa-solid ${def.icon}"></i> ${def.label}</span>` +
            `<span class="jp-btn-sub">${def.sub}</span>` +
          `</a>`;
      }
      // important_links object
      const ilRaw = rawJob.important_links || rawJob.important_links_obj || {};
      const ilMap = [
        { keys: ['apply_online','apply_link','click_here_to_apply'],        label: 'Apply Online',          icon: 'fa-paper-plane', cls: 'jp-btn-green',  sub: 'Apply Now'    },
        { keys: ['notification_pdf','download_notification','download_pdf'], label: 'Official Notification', icon: 'fa-file-pdf',    cls: 'jp-btn-blue',   sub: 'Download PDF' },
        { keys: ['official_website','visit_website'],                        label: 'Official Website',      icon: 'fa-globe',       cls: 'jp-btn-red',    sub: 'Visit Now'    },
        { keys: ['result','result_link'],                                    label: 'Result',                icon: 'fa-trophy',      cls: 'jp-btn-orange', sub: 'View Now'     },
        { keys: ['admit_card','admit_card_link'],                            label: 'Admit Card',            icon: 'fa-id-card',     cls: 'jp-btn-orange', sub: 'Download Now' },
      ];
      if (typeof ilRaw === 'object' && !Array.isArray(ilRaw)) {
        for (const ilDef of ilMap) {
          let ilUrl = '';
          for (const k of ilDef.keys) {
            const kval = ilRaw[k];
            if (kval) { ilUrl = safe(Array.isArray(kval) ? kval[0] : kval); if (ilUrl) break; }
          }
          if (!ilUrl) continue;
          const ilHref = normUrl(ilUrl);
          if (!ilHref || shown.has(ilHref)) continue;
          shown.add(ilHref);
          newHtml +=
            `<a href="${ilHref}" target="_blank" rel="noopener" class="jp-btn ${ilDef.cls}">` +
              `<span><i class="fa-solid ${ilDef.icon}"></i> ${ilDef.label}</span>` +
              `<span class="jp-btn-sub">${ilDef.sub}</span>` +
            `</a>`;
        }
      }
      if (newHtml) {
        const placeholder = container.querySelector('p');
        if (placeholder) placeholder.remove();
        container.insertAdjacentHTML('beforeend', newHtml);
      }
    }
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 11 — MASTER INJECTOR
     UNIFORM layout: same card sequence for EVERY job.
     No conditional layout changes based on missing fields.
     Data normalizes to "N/A" / fallback — layout never changes.
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

  /* ── FSCD link categorizer ── */
  function fscdLinkCat(title) {
    const t = title.toLowerCase();
    if (/apply\s*online|apply\s*link|apply\s*form|apply.*otr|registration\s*link|apply.*mains|apply.*re\s*open/i.test(t))
      return { icon:'fa-paper-plane', cls:'ib-gr', sub:'Apply Now' };
    if (/candidate\s*login|login\s*portal/i.test(t))
      return { icon:'fa-right-to-bracket', cls:'ib-gr', sub:'Login' };
    if (/admit\s*card|hall\s*ticket|call\s*letter/i.test(t))
      return { icon:'fa-id-card', cls:'ib-or', sub:'Download' };
    if (/result|merit\s*list|score\s*card|cutoff/i.test(t))
      return { icon:'fa-trophy', cls:'ib-or', sub:'View' };
    if (/answer\s*key|final\s*answer/i.test(t))
      return { icon:'fa-key', cls:'ib-bl', sub:'Download' };
    if (/notification|download.*notif|download.*pdf|official.*notif|short.*notice/i.test(t))
      return { icon:'fa-file-pdf', cls:'ib-bl', sub:'View PDF' };
    if (/syllabus|exam.*pattern/i.test(t))
      return { icon:'fa-book-open', cls:'ib-bl', sub:'Download' };
    if (/official\s*website|official\s*portal|visit.*website/i.test(t))
      return { icon:'fa-globe', cls:'ib-rd', sub:'Visit' };
    if (/counselling|seat\s*allotment/i.test(t))
      return { icon:'fa-graduation-cap', cls:'ib-pu', sub:'Counselling' };
    if (/correction|edit\s*form/i.test(t))
      return { icon:'fa-pen-to-square', cls:'ib-te', sub:'Edit' };
    if (/exam\s*city|exam\s*centre/i.test(t))
      return { icon:'fa-location-dot', cls:'ib-bl', sub:'Check' };
    return { icon:'fa-link', cls:'ib-bl', sub:'Open Link' };
  }

  /* ── FSCD: render icon link grid from _udyn_links array ── */
  function fscdIconLinks(links) {
    if (!links || !links.length) return '';
    const seen = new Set();
    const filtered = links.filter(lk => {
      const h = (lk.href || lk.url || '').trim();
      if (!h || h === '#' || seen.has(h)) return false;
      seen.add(h);
      return true;
    });
    if (!filtered.length) return '';
    return `<div class="fscd-icon-links">${filtered.map(lk => {
      const href = lk.href || lk.url || '#';
      const label = lk.label || lk.title || 'Link';
      const cat = fscdLinkCat(label);
      return `<a href="${esc(href)}" target="_blank" rel="noopener" class="fscd-ib ${cat.cls}">`
        +`<div class="fscd-ib-ico"><i class="fa-solid ${cat.icon}"></i></div>`
        +`<div class="fscd-ib-lbl">${esc(label.slice(0,26))}</div>`
        +`<div class="fscd-ib-sub">${cat.sub}</div>`
        +`</a>`;
    }).join('')}</div>`;
  }

  function injectAllSections(rawJob) {
    if (!rawJob || typeof rawJob !== 'object') return;
    const layout = document.getElementById('layoutJob');
    if (!layout || layout.style.display === 'none') return;

    clearUniversalCards();
    layout.classList.add('fscd-active');

    /* ── Extract all data ── */
    const bd      = rawJob.basic_details   || {};
    const id      = rawJob.important_dates || {};
    const fee     = rawJob.application_fee || rawJob.application_fees || {};
    const age     = rawJob.age_limit       || {};
    const sd      = rawJob.salary_details  || {};

    const title     = safe(rawJob.title || rawJob.name_of_post || rawJob.post_name || bd.job_title || bd.post_name || '');
    const org       = safe(rawJob.organization || rawJob.board_name || bd.organization_name || '');
    const location  = safe(bd.job_location || rawJob.location || rawJob.state || 'Pan-India');
    const totalVac  = safe(rawJob.total_vacancy || rawJob.total_vacancies || bd.total_vacancies || bd.total_post || '');
    const applyMode = safe(rawJob.apply_mode || rawJob.application_mode || bd.application_mode || 'Online');
    const shortInfo = safe(rawJob.short_information || rawJob.jobs_info || bd.short_information || '');
    const category  = safe(rawJob.category || '');

    /* ── Clean shortInfo of junk ── */
    function cleanShort(s) {
      return s
        .replace(/telegram\s+join\s+us\s+whatsapp\s+join\s+us\s+instagram\s+follow\s+(x|twitter)\s+follow/gi, '')
        .replace(/sarkari\s*result[®@]?\s*[:–-]?\s*sarkariresult\.com\s+official\s+since\s*:\s*\d*/gi, '')
        .replace(/\s*(sbi|crpd)\s+advt\s+no\.\s*:\s*[A-Z0-9\/\-]+\s*:/gi, ' ')
        .replace(/short\s+details\s+of\s+notification\s*$/gi, '')
        .replace(/\s{2,}/g, ' ').trim();
    }
    const shortInfoClean = cleanShort(shortInfo);

    /* ── Dates ── */
    const lastDate  = fmtDate(safe(id.last_date || id.last_date_to_apply || id.application_last_date || rawJob.last_date || ''));
    const appBegin  = fmtDate(safe(id.application_begin || id.application_start || id.start_date || ''));
    const examDate  = fmtDate(safe(id.exam_date || rawJob.exam_date || ''));
    const admitDate = fmtDate(safe(id.admit_card_date || id.admit_card || ''));
    const feeLastDate = fmtDate(safe(id.last_date_fee_payment || id.fee_payment_last_date || ''));
    const corrDate  = fmtDate(safe(id.correction_date || id.last_date_correction || ''));
    const resultDate= fmtDate(safe(id.result_date || ''));
    const notifDate = fmtDate(safe(id.notification_date || id.date_of_notification || rawJob.post_date || ''));

    /* ── Age ── */
    function isJunk(s) {
      if (!s) return true;
      return /telegram|whatsapp|instagram|follow|sarkari result|freejobalert|click here|advt no\.|short details/i.test(s);
    }
    const minAge  = safe(rawJob.minimum_age || age.minimum_age || age.min_age || '');
    const maxAge  = safe(rawJob.maximum_age || age.maximum_age || age.max_age || '');
    const ageRaw  = safe(age.raw || '');
    const ageDet  = safe(age.age_details || age.details || '');
    const ageRelax= safe(rawJob.age_relaxation || age.age_relaxation || age.relaxation || '');
    // Also try to pull from FAQ (SBI pattern)
    let faqMin = '', faqMax = '';
    const faqArr = Array.isArray(rawJob.faq) ? rawJob.faq : [];
    for (const f of faqArr) {
      const ans = safe(f.answer || f.a || '').toLowerCase();
      const q   = safe(f.question || f.q || '');
      if (/minimum age/i.test(ans) && /^\d+/.test(q)) faqMin = q;
      if (/maximum age/i.test(ans) && /^\d+/.test(q)) faqMax = q;
    }
    const finalMinAge = (!isJunk(minAge) && minAge) ? minAge : faqMin;
    const finalMaxAge = (!isJunk(maxAge) && maxAge) ? maxAge : faqMax;
    const finalAgeRelax = (!isJunk(ageRelax)) ? ageRelax : '';
    const finalAgeDet = (!isJunk(ageDet) && !isJunk(ageRaw))
      ? (ageDet || '')
      : (!isJunk(ageRaw) ? ageRaw : '');

    /* ── Salary ── */
    const salaryPay = safe(rawJob.salary || rawJob.salary_pay_scale || bd.salary || sd.pay_scale || '');
    const salaryDet = safe(sd.details || sd.salary_details || '');

    /* ── Vacancy rows (filtered) ── */
    const { rows: vacRows, cw: vacCW } = exVacancy(rawJob);

    /* ── Links ── */
    const links = (rawJob._udyn_links || []).filter(l => l && l.url && l.label);

    /* ── Qual / Eligibility ── */
    const qual = rawJob.qualification || rawJob.eligibility || {};

    /* ── Selection / How-to / Instructions / FAQ ── */
    const selProc = rawJob.selection_process || [];
    const howTo   = Array.isArray(rawJob.how_to_apply) ? rawJob.how_to_apply : [];
    const insts   = Array.isArray(rawJob.important_instructions || rawJob.instructions) ? (rawJob.important_instructions || rawJob.instructions) : [];
    const faqs    = Array.isArray(rawJob.faq) ? rawJob.faq : [];

    /* ── Helper: section card builder (Image 2 style) ── */
    function sec(id, bgColor, iconCls, headText, bodyHtml) {
      if (!bodyHtml || bodyHtml.trim() === '') return null;
      const d = document.createElement('div');
      d.className = 'udyn-card udyn-anchor';
      d.id = id;
      d.innerHTML =
        `<div class="udyn-head" style="background:${bgColor}">` +
          `<i class="${iconCls}"></i> ${esc(headText)}` +
        `</div><div class="udyn-body">${bodyHtml}</div>`;
      return d;
    }

    /* ── Helper: key-value table row ── */
    function kvRow(label, val, redVal) {
      if (!val) return '';
      return `<tr><th>${esc(label)}</th><td style="${redVal ? 'color:#dc2626;font-weight:700;' : ''}">${esc(val)}</td></tr>`;
    }

    /* ── Helper: append card ── */
    function appendCard(card) {
      if (card) layout.appendChild(card);
    }

    /* ═══════════════════════════════════════════
       SECTION 1: JOB OVERVIEW (Image 2 style)
    ═══════════════════════════════════════════ */
    const overviewRows = [
      org           ? `<tr><th>Organization Name</th><td>${esc(org)}</td></tr>` : '',
      bd.post_name||rawJob.post_name  ? `<tr><th>Post Name</th><td>${esc(safe(bd.post_name||rawJob.post_name||rawJob.name_of_post||''))}</td></tr>` : '',
      totalVac      ? `<tr><th>Total Vacancies</th><td><strong style="color:#16a34a">${esc(totalVac)}</strong></td></tr>` : '',
      applyMode     ? `<tr><th>Application Mode</th><td>${esc(applyMode)}</td></tr>` : '',
      location      ? `<tr><th>Job Location</th><td>${esc(location)}</td></tr>` : '',
      (rawJob.job_type||bd.job_type)  ? `<tr><th>Job Type</th><td>${esc(safe(rawJob.job_type||bd.job_type||''))}</td></tr>` : '',
      (rawJob.notification_number||bd.notification_number) ? `<tr><th>Notification Number</th><td>${esc(safe(rawJob.notification_number||bd.notification_number||''))}</td></tr>` : '',
      (rawJob.last_updated||bd.last_updated||rawJob.post_date) ? `<tr><th>Last Updated</th><td>${esc(safe(rawJob.last_updated||bd.last_updated||rawJob.post_date||''))}</td></tr>` : '',
    ].filter(Boolean).join('');

    /* Short info block below overview table */
    const shortInfoBlock = shortInfoClean
      ? `<div style="background:#eef4fa;border-left:4px solid #1e7e9f;padding:10px 14px;font-size:.83rem;color:#165e7c;line-height:1.75;margin:0;">${esc(shortInfoClean)}</div>`
      : '';

    const overviewCard = sec('udyn-overview','linear-gradient(135deg,#0369a1,#0284c7)',
      'fa-solid fa-circle-info','Job Overview',
      (overviewRows ? `<div class="udyn-table-scroll"><table class="udyn-gen-table">${overviewRows}</table></div>` : '') + shortInfoBlock
    );
    appendCard(overviewCard);

    /* ═══════════════════════════════════════════
       SECTION 2: IMPORTANT DATES
    ═══════════════════════════════════════════ */
    const dateRows = [
      appBegin    ? kvRow('Application Begin', appBegin) : '',
      lastDate    ? `<tr><th>Last Date To Apply</th><td style="color:#dc2626;font-weight:700;">${esc(lastDate)}</td></tr>` : '',
      feeLastDate ? kvRow('Last Date Fee Payment', feeLastDate) : '',
      corrDate    ? kvRow('Correction Date', corrDate) : '',
      examDate    ? kvRow('Exam Date', examDate) : '',
      admitDate   ? kvRow('Admit Card Available', admitDate) : '',
      resultDate  ? kvRow('Result Date', resultDate) : '',
      notifDate   ? kvRow('Notification Date', notifDate) : '',
    ].filter(Boolean).join('');

    // Also add any extra date fields from important_dates
    const knownDateKeys = new Set(['application_begin','application_start','start_date','last_date','last_date_to_apply','application_last_date','exam_date','admit_card_date','admit_card','result_date','notification_date','date_of_notification','last_date_fee_payment','fee_payment_last_date','correction_date','last_date_correction','raw','rawDate']);
    let extraDateRows = '';
    for (const [k, v] of Object.entries(id)) {
      if (knownDateKeys.has(k) || !hasContent(v) || k.startsWith('_')) continue;
      const fv = fmtDate(safe(v));
      if (fv) extraDateRows += kvRow(keyToLabel(k), fv);
    }

    if (dateRows || extraDateRows) {
      appendCard(sec('udyn-dates','linear-gradient(135deg,#b91c1c,#dc2626)',
        'fa-regular fa-calendar-check','Important Dates',
        `<div class="udyn-table-scroll"><table class="udyn-gen-table">${dateRows}${extraDateRows}</table></div>`
      ));
    }

    /* ═══════════════════════════════════════════
       SECTION 3: APPLICATION FEE
    ═══════════════════════════════════════════ */
    const feeData = exFees(rawJob);
    if (feeData.items.length) {
      const isFree = v => /nil|^0\/?-?$|free|no fee|exempt/i.test(String(v).trim());
      const feeGridHtml = feeData.items.map(({ label, val }) =>
        `<div class="udyn-grid-item">` +
          `<div class="udyn-grid-label">${esc(label)}</div>` +
          `<div class="udyn-grid-val" style="${isFree(val) ? 'color:#16a34a;' : 'color:#1d4ed8;'}">${esc(val)}</div>` +
        `</div>`
      ).join('');
      const feeNoteHtml = feeData.note
        ? `<div class="udyn-grid-note"><i class="fa-solid fa-circle-info" style="margin-right:5px;"></i>${esc(feeData.note)}</div>`
        : '';
      appendCard(sec('udyn-fee','linear-gradient(135deg,#c2410c,#ea580c)',
        'fa-solid fa-indian-rupee-sign','Application Fee',
        `<div class="udyn-grid" style="grid-template-columns:repeat(auto-fill,minmax(170px,1fr));">${feeGridHtml}</div>${feeNoteHtml}`
      ));
    }

    /* ═══════════════════════════════════════════
       SECTION 4: AGE LIMIT
    ═══════════════════════════════════════════ */
    const ageRows = [
      finalMinAge  ? kvRow('Minimum Age', finalMinAge) : '',
      finalMaxAge  ? kvRow('Maximum Age', finalMaxAge) : '',
      finalAgeRelax? kvRow('Age Relaxation', finalAgeRelax) : '',
    ].filter(Boolean).join('');
    const ageDetLong = finalAgeDet && finalAgeDet.length > 80 && !isJunk(finalAgeDet);
    const ageDetShort = finalAgeDet && finalAgeDet.length <= 80 && !isJunk(finalAgeDet);
    const ageDetHtml = ageDetShort ? kvRow('Age Details', finalAgeDet) : '';
    const ageDetBlock = ageDetLong
      ? `<div class="udyn-detail" style="font-size:.82rem;line-height:1.8;color:#374151;white-space:pre-line;">${esc(finalAgeDet)}</div>`
      : '';

    if (ageRows || ageDetHtml || ageDetBlock) {
      appendCard(sec('udyn-age','linear-gradient(135deg,#7c3aed,#8b5cf6)',
        'fa-solid fa-user-clock','Age Limit',
        `<div class="udyn-table-scroll"><table class="udyn-gen-table">${ageRows}${ageDetHtml}</table></div>${ageDetBlock}`
      ));
    }

    /* ═══════════════════════════════════════════
       SECTION 5: QUALIFICATION / ELIGIBILITY
    ═══════════════════════════════════════════ */
    const qualContent = deepRender(qual, 0);
    const eligText = safe(rawJob.eligibility || '');
    // Try to extract eligibility table from SR tables (3-col: Post Name | Total Post | Eligibility)
    let eligTableHtml = '';
    if (rawJob.tables && Array.isArray(rawJob.tables)) {
      for (const grp of rawJob.tables) {
        if (!grp || !Array.isArray(grp.rows)) continue;
        const eligRows = grp.rows.filter(r => Array.isArray(r) && r.length === 3 &&
          /eligibility|pharmacist|x-ray|lab technician|diploma|intermediate|pharmacy|radiography/i.test(r.join(' ')));
        if (eligRows.length > 0) {
          // Find header row
          const headerRow = grp.rows.find(r => Array.isArray(r) && r.length === 3 &&
            /post.*name|eligib/i.test(r.join(' ')) &&
            eligRows.indexOf(r) === -1);
          const thead = headerRow
            ? `<thead><tr>${headerRow.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>`
            : `<thead><tr><th>Post Name</th><th>Total Post</th><th>Eligibility</th></tr></thead>`;
          const tbody = eligRows.map(r =>
            `<tr>${r.map(c => `<td>${esc(safe(c))}</td>`).join('')}</tr>`
          ).join('');
          eligTableHtml = `<div class="udyn-table-scroll"><table class="udyn-vac-table">${thead}<tbody>${tbody}</tbody></table></div>`;
          break;
        }
      }
    }
    if (qualContent || eligText || eligTableHtml) {
      let qHtml = '';
      if (eligTableHtml) {
        qHtml = eligTableHtml;
      } else if (qualContent) {
        qHtml = `<div class="udyn-detail" style="line-height:1.8;">${qualContent}</div>`;
      } else {
        qHtml = `<div class="udyn-detail" style="font-size:.83rem;line-height:1.8;">${esc(eligText)}</div>`;
      }
      appendCard(sec('udyn-qual','linear-gradient(135deg,#0369a1,#0284c7)',
        'fa-solid fa-graduation-cap','Qualification / Eligibility', qHtml));
    }

    /* ═══════════════════════════════════════════
       SECTION 6: VACANCY DETAILS
    ═══════════════════════════════════════════ */
    const vacCard = cardVacancy(vacRows, vacCW);
    if (vacCard) appendCard(vacCard);

    /* ═══════════════════════════════════════════
       SECTION 7: CATEGORY-WISE VACANCY (standalone if large)
    ═══════════════════════════════════════════ */
    // Already merged into vacCard above via cardVacancy

    /* ═══════════════════════════════════════════
       SECTION 8: SALARY / PAY SCALE
    ═══════════════════════════════════════════ */
    const salData = exSalary(rawJob); const salCard = cardSalary(salData.structured, salData.flat);
    if (salCard) appendCard(salCard);

    /* ═══════════════════════════════════════════
       SECTION 9: SELECTION PROCESS
    ═══════════════════════════════════════════ */
    const selCard = cardSelection(selProc);
    if (selCard) appendCard(selCard);

    /* ═══════════════════════════════════════════
       SECTION 10: EXAM PATTERN / SYLLABUS
    ═══════════════════════════════════════════ */
    const ep = rawJob.exam_pattern;
    const syl = rawJob.syllabus;
    if (ep) appendCard(cardExamPattern(ep));
    if (syl) appendCard(cardSyllabus(syl));

    /* ═══════════════════════════════════════════
       SECTION 11: PHYSICAL ELIGIBILITY
    ═══════════════════════════════════════════ */
    const pe = rawJob.physical_eligibility || rawJob.physical_standards;
    if (pe) appendCard(cardPhysical(pe));

    /* ═══════════════════════════════════════════
       SECTION 12: HOW TO APPLY
    ═══════════════════════════════════════════ */
    const htaCard = cardHowToApply(howTo);
    if (htaCard) appendCard(htaCard);

    /* ═══════════════════════════════════════════
       SECTION 13: IMPORTANT LINKS
    ═══════════════════════════════════════════ */
    if (links.length) appendCard(cardLinks(links));

    /* ═══════════════════════════════════════════
       SECTION 14: INSTRUCTIONS
    ═══════════════════════════════════════════ */
    if (insts.length) appendCard(cardInstructions(insts));

    /* ═══════════════════════════════════════════
       SECTION 15: SR-STYLE TABLES (deduplicated)
    ═══════════════════════════════════════════ */
    const tables = exTables(rawJob);
    if (tables && Array.isArray(tables)) {
      const filteredTables = tables.filter(group => {
        if (!group || !Array.isArray(group.rows)) return true;
        const tname = safe(group.table_name || '').toLowerCase();
        // Skip tables that just duplicate vacancy/overview data already shown
        if (/post name|total post|sbi apprent|post wise|gb headline|short details of notification|name of post/i.test(tname)) return false;
        // Skip tables where every row is overview info (Name Of Post, Short Information)
        const rowTexts = group.rows.map(r => Array.isArray(r) ? r.join(' ') : '').join(' ').toLowerCase();
        if (/name of post|short information|post date.*update/i.test(rowTexts) && group.rows.length <= 3) return false;
        // For tables with long age-limit heading: strip heading, filter out eligibility rows (already in Qual section)
        // keep only vacancy category rows + links; check BEFORE vacancy dedup filter
        if (/age limit|age relaxation|minimum age|maximum age/i.test(tname)) {
          const filteredRows = group.rows.filter(r => {
            if (!Array.isArray(r)) return false;
            const joined = r.join(' ').toLowerCase();
            // Remove eligibility rows (3-col with eligibility/post qualification text)
            if (r.length === 3 && /eligibility|pharmacist|x-ray|lab technician|diploma|intermediate|pharmacy|radiography/i.test(joined)) return false;
            return true;
          });
          if (!filteredRows.length) return false;
          group.rows = filteredRows;
          group.table_name = '';
          return true;
        }
        // Skip if vacancy already rendered and table has vacancy structure (only pure vacancy tables)
        if (vacRows.length > 0 && /vacancy|ur.*general|ews.*obc/i.test(rowTexts)) return false;
        return true;
      });
      if (filteredTables.length > 0) {
        const tc = cardTables(filteredTables);
        if (tc) appendCard(tc);
      }
    }

    /* ═══════════════════════════════════════════
       SECTION 16: TEXT SECTIONS
    ═══════════════════════════════════════════ */
    const textSections = exTextSections(rawJob);
    if (textSections) {
      const ts = cardTextSections(textSections);
      if (ts) appendCard(ts);
    }

    /* ═══════════════════════════════════════════
       SECTION 17: FAQs (deduped + Q/A fixed)
    ═══════════════════════════════════════════ */
    if (faqs.length) appendCard(cardFaq(faqs));

    updateTOC(document.querySelectorAll('.udyn-card.udyn-anchor'));
  }



  /* ═══════════════════════════════════════════════════════════════════════
     § 12 — FALLBACK: SEARCH FULL DATA FOR SLUG MATCH
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
      const r = await fetch('/data/Complete_Jobs_Full_Data.json');
      if (r.ok) {
        const d = await r.json();
        // Collect ALL jobs from every source in the JSON
        const jobs = [];
        if (Array.isArray(d)) {
          jobs.push(...d);
        } else if (typeof d === 'object') {
          // freejobalert_categories: { CAT_KEY: [job, job, ...], ... }
          for (const [k, v] of Object.entries(d)) {
            if (k === 'sarkari_data' && v && Array.isArray(v.jobs)) {
              jobs.push(...v.jobs);
            } else if (k === 'education_jobs' || k === 'state_jobs') {
              const secs = (v && v.sections) || [];
              for (const sec of secs) {
                if (Array.isArray(sec.items)) jobs.push(...sec.items.filter(it => it && it.detail).map(it => it.detail));
              }
            } else if (typeof v === 'object' && !Array.isArray(v)) {
              // Could be nested category
              for (const [, cv] of Object.entries(v)) {
                if (Array.isArray(cv)) jobs.push(...cv);
              }
            } else if (Array.isArray(v)) {
              jobs.push(...v);
            }
          }
        }
        for (const job of jobs) {
          if (!job || typeof job !== 'object') continue;
          const t = safe(job.title || (job.basic_details && job.basic_details.job_title) || job.post_name || '');
          const sc = scoreMatch(t, tokens);
          if (sc > bestScore) { bestScore = sc; best = job; }
        }
      }
    } catch (_) {}

    if (best && bestScore >= 0.75) {
      let pre = best;
      try { pre = normalizeUpcomingJobsSections(best); } catch (_) {}
      const normalized = normalizeJob(pre);
      injectAllSections(normalized);
      runBasePatches(normalized);
    }
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 13 — INTEGRATION HUB
     Race-condition-free. Works whether this script loads before or after
     job.html finishes rendering (no job-renderer-patch.js needed).
  ═══════════════════════════════════════════════════════════════════════ */

  function onJobRendered(rawJob) {
    let job = rawJob;
    if (job && typeof job === 'object') {
      try { job = normalizeUpcomingJobsSections(job); } catch(e) {}
      job = normalizeJob(job);
      try { injectAllSections(job); } catch(e) {}
      try { runBasePatches(job); } catch(e) {}
    } else {
      setTimeout(findAndEnrichFromFullData, 200);
    }
  }

  (function integrate() {
    // Case 1: Already rendered (cached / fast network)
    if (window.__TSJ_RENDER_DONE) {
      setTimeout(() => onJobRendered(window.__TSJ_RAW_JOB), 0);
      return;
    }

    // Case 2: Register callback (job.html fires this in finally{})
    window.__TSJ_ON_RENDER_DONE = function(rawJob) {
      setTimeout(() => onJobRendered(rawJob), 0);
    };

    // Case 3: SEO Engine hook
    window.__SEO_ENGINE_JOB_READY = function(seoJob) {
      if (window.__TSJ_RAW_JOB) return;
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
/* ══ END Universal Dynamic JSON-to-Page Rendering Engine v4.0 ══ */