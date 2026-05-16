/**
 * ============================================================
 * TOP SARKARI JOBS — HERO SEARCH (Simple & Optimized)
 * Version: 3.0
 *
 * Features:
 *  - 4 JSON sources: merged_sarkari_data.json, dailyupdates.json,
 *                    Complete_Jobs_Full_Data.json, state-jobs-data.json
 *  - Search by: Job Name, Post Name, Department, Category,
 *               Qualification, State
 *  - Results show: Job Title + Direct job.html URL
 *  - Click → correct job page opens directly
 *  - Live dropdown suggestions while typing
 *  - Keyboard navigation (↑↓ Enter Esc)
 *  - Debounced input (200ms)
 *  - Phased JSON loading (fast first, heavy in background)
 * ============================================================
 */
(function () {
  'use strict';

  /* ═══════════════════════════════════════════════════════════
     CONFIG
  ═══════════════════════════════════════════════════════════ */
  var CFG = {
    maxSuggest : 10,   // dropdown suggestions
    debounceMs : 200,
    recentKey  : 'tsj_hero_recent',
    maxRecent  : 6,
  };

  /* ═══════════════════════════════════════════════════════════
     STATE
  ═══════════════════════════════════════════════════════════ */
  var allJobs      = [];   // all indexed job items
  var phase1Ready  = false; // merged_sarkari + dailyupdates done
  var activeIdx    = -1;
  var suggestList  = [];

  /* ═══════════════════════════════════════════════════════════
     UTILS
  ═══════════════════════════════════════════════════════════ */
  function esc(s) {
    return String(s || '').replace(/[&<>"]/g, function(c) {
      return { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c];
    });
  }

  function debounce(fn, ms) {
    var t;
    return function() {
      var args = arguments, ctx = this;
      clearTimeout(t);
      t = setTimeout(function() { fn.apply(ctx, args); }, ms);
    };
  }

  /* Highlight matching query words in text */
  function highlight(text, q) {
    if (!q || !text) return esc(text);
    var words = q.trim().split(/\s+/).filter(function(w){ return w.length > 1; });
    var out = esc(text);
    words.forEach(function(w) {
      var rx = new RegExp('(' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      out = out.replace(rx, '<mark class="hs-hl">$1</mark>');
    });
    return out;
  }

  /* Recent searches */
  function getRecent() {
    try { return JSON.parse(localStorage.getItem(CFG.recentKey) || '[]'); } catch(e) { return []; }
  }
  function saveRecent(q) {
    if (!q || q.length < 2) return;
    var list = getRecent().filter(function(r){ return r.toLowerCase() !== q.toLowerCase(); });
    list.unshift(q);
    list = list.slice(0, CFG.maxRecent);
    try { localStorage.setItem(CFG.recentKey, JSON.stringify(list)); } catch(e) {}
  }

  /* ═══════════════════════════════════════════════════════════
     SLUG / URL BUILDER
     Job URL always: job.html?slug=<slug>&section=<section>
  ═══════════════════════════════════════════════════════════ */
  function makeJobUrl(slug, section) {
    if (!slug) return '#';

    // Already a full relative path like "job.html?slug=..."
    if (slug.indexOf('job.html') === 0) return slug;

    // External URL — skip
    if (/^https?:\/\//i.test(slug)) return slug;

    // Build job.html?slug=...&section=...
    var url = 'job.html?slug=' + encodeURIComponent(slug);
    if (section) url += '&section=' + encodeURIComponent(section);
    return url;
  }

  /* Build a slug from a job title (fallback when no slug provided) */
  function slugifyTitle(title) {
    return String(title || '')
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .slice(0, 80);
  }

  /* ═══════════════════════════════════════════════════════════
     DEDUPLICATION
  ═══════════════════════════════════════════════════════════ */
  var _seen = new Set ? new Set() : (function() {
    var a = [];
    return { has: function(v){ return a.indexOf(v) !== -1; }, add: function(v){ a.push(v); } };
  })();

  function addJob(item) {
    var key = item.url.split('?')[0].toLowerCase() + '::' + (item.title || '').toLowerCase().slice(0, 40);
    if (_seen.has(key)) return;
    _seen.add(key);
    allJobs.push(item);
  }

  /* ═══════════════════════════════════════════════════════════
     JSON PARSERS — one per file, extract { title, url, meta }
  ═══════════════════════════════════════════════════════════ */

  /* 1. merged_sarkari_data.json
     { jobs: [{title, post_name, organization, qualification, job_location,
               important_dates:{last_date}, slug, sr_category, ...}],
       sarkariresult_categories: { SR_Latest_Jobs:[...], ... } }
  */
  function parseMergedSarkari(data) {
    var count = 0;
    var SR_SEC = {
      SR_Latest_Jobs : 'Latest Jobs',
      SR_Admit_Card  : 'Admit Card',
      SR_Result      : 'Result',
      SR_Admission   : 'Admission',
      SR_Answer_Key  : 'Answer Key',
      SR_Offline_Form: 'Offline Form',
    };

    // jobs[]
    var jobs = Array.isArray(data.jobs) ? data.jobs : [];
    jobs.forEach(function(j) {
      var title = (j.title || j.post_name || '').trim();
      if (!title) return;

      var section = 'Latest Jobs';
      var url;

      if (j.slug) {
        // slug already has section encoded sometimes, keep as-is
        url = j.slug.indexOf('job.html') === 0 ? j.slug : makeJobUrl(j.slug, section);
      } else {
        var slug = slugifyTitle(title);
        if (!slug) return;
        var catKey = j.sr_category || '';
        section = SR_SEC[catKey] || 'Latest Jobs';
        url = 'job.html?slug=sr_' + catKey.toLowerCase().replace('sr_','') + '-' + slug + '&section=' + encodeURIComponent(section);
      }

      addJob({
        title   : title,
        url     : url,
        dept    : j.organization || j.board_name || j.department || '',
        post    : j.post_name || '',
        qual    : j.qualification || j.eligibility || '',
        state   : j.job_location || j.state || 'All India',
        cat     : j.sr_category ? (SR_SEC[j.sr_category] || 'Latest Job') : 'Latest Job',
        section : section,
        tags    : [title, j.post_name, j.organization, j.qualification, j.job_location, j.short_information].filter(Boolean).join(' '),
      });
      count++;
    });

    // sarkariresult_categories
    var srCats = data.sarkariresult_categories || {};
    Object.keys(srCats).forEach(function(key) {
      var section = SR_SEC[key] || key;
      var arr = Array.isArray(srCats[key]) ? srCats[key] : [];
      arr.forEach(function(item) {
        var title = (item.title || item.name || '').trim();
        if (!title) return;
        var url = item.slug
          ? makeJobUrl(item.slug, section)
          : (item.url || item.source_url || '#');
        if (url === '#') return;
        addJob({
          title   : title,
          url     : url,
          dept    : item.org || item.organization || '',
          post    : '',
          qual    : '',
          state   : '',
          cat     : section,
          section : section,
          tags    : title + ' ' + section,
        });
        count++;
      });
    });

    console.log('[hero-search] merged_sarkari_data → ' + count + ' jobs');
  }

  /* 2. dailyupdates.json
     { sections:[{id, title, items:[{name, url, slug, date}]}] }
     Only internal job.html links are indexed.
  */
  function parseDailyUpdates(data) {
    var count = 0;
    var sections = Array.isArray(data.sections) ? data.sections
                 : Array.isArray(data) ? data : [];

    sections.forEach(function(sec) {
      var secTitle = (sec.title || sec.id || '').trim();
      var items = Array.isArray(sec.items) ? sec.items : [];

      items.forEach(function(item) {
        var title = (item.name || item.title || '').trim();
        if (!title) return;

        // Only internal links
        var url = '';
        if (item.slug) {
          url = makeJobUrl(item.slug, secTitle);
        } else if (item.url && item.url.indexOf('job.html') === 0) {
          url = item.url;
        } else {
          return; // skip external links
        }

        addJob({
          title   : title,
          url     : url,
          dept    : secTitle,
          post    : '',
          qual    : '',
          state   : '',
          cat     : secTitle,
          section : secTitle,
          tags    : title + ' ' + secTitle,
        });
        count++;
      });
    });

    console.log('[hero-search] dailyupdates → ' + count + ' jobs');
  }

  /* 3. Complete_Jobs_Full_Data.json
     { Railway_Jobs:[...], Bank_Jobs:[...], SSC_Jobs:[...], ... }
     Each item: { title, slug, organization, basic_details:{...},
                  important_dates:{last_date}, qualification }
  */
  var COMPLETE_CATS = {
    Railway_Jobs    : { label:'Railway Jobs',    section:'Railway Jobs'    },
    Bank_Jobs       : { label:'Bank Jobs',       section:'Bank Jobs'       },
    SSC_Jobs        : { label:'SSC Jobs',        section:'SSC Jobs'        },
    Police_Jobs     : { label:'Police Jobs',     section:'Police Jobs'     },
    Defence_Jobs    : { label:'Defence Jobs',    section:'Defence Jobs'    },
    Teaching_Jobs   : { label:'Teaching Jobs',   section:'Teaching Jobs'   },
    PSU_Jobs        : { label:'PSU Jobs',        section:'PSU Jobs'        },
    Medical_Jobs    : { label:'Medical Jobs',    section:'Medical Jobs'    },
    ITI_Jobs        : { label:'ITI Jobs',        section:'ITI Jobs'        },
    Admit_Card      : { label:'Admit Card',      section:'Admit Card'      },
    Result          : { label:'Result',          section:'Result'          },
    Answer_Key      : { label:'Answer Key',      section:'Answer Key'      },
    Admission       : { label:'Admission',       section:'Admission'       },
    Offline_Form    : { label:'Offline Form',    section:'Offline Form'    },
    Latest_Jobs     : { label:'Latest Jobs',     section:'Latest Jobs'     },
  };

  function parseCompleteJobs(data) {
    if (!data || typeof data !== 'object' || Array.isArray(data)) return;
    var total = 0;

    Object.keys(data).forEach(function(key) {
      var arr = Array.isArray(data[key]) ? data[key] : [];
      if (!arr.length) return;

      var meta = COMPLETE_CATS[key] || { label: key.replace(/_/g,' '), section: key.replace(/_/g,' ') };

      arr.forEach(function(job) {
        var bd    = job.basic_details || {};
        var title = (job.title || bd.job_title || job.post_name || '').trim();
        if (!title) return;

        var url;
        if (job.slug) {
          url = makeJobUrl(job.slug, meta.section);
        } else {
          var slug = slugifyTitle(bd.job_title || title);
          if (!slug) return;
          url = 'job.html?slug=' + encodeURIComponent(key.toLowerCase().replace(/_/g,'-') + '-' + slug)
              + '&section=' + encodeURIComponent(meta.section);
        }

        var org  = (job.organization || job.board_name || bd.organization_name || bd.department || '').trim();
        var qual = (job.qualification || bd.qualification || '').trim();

        addJob({
          title   : title,
          url     : url,
          dept    : org,
          post    : (bd.post_name || job.post_name || '').trim(),
          qual    : qual,
          state   : (job.state || 'All India').trim(),
          cat     : meta.label,
          section : meta.section,
          tags    : [title, org, qual, bd.post_name, job.total_vacancies, bd.short_information].filter(Boolean).join(' '),
        });
        total++;
      });
    });

    console.log('[hero-search] Complete_Jobs_Full_Data → ' + total + ' jobs');
  }

  /* 4. state-jobs-data.json
     { sections:[{id, title, state, items:[{name, url, qualification, board, detail:{...}}]}] }
  */
  function parseStateJobs(data) {
    var count = 0;
    var sections = Array.isArray(data.sections) ? data.sections
                 : Array.isArray(data) ? data : [];

    sections.forEach(function(sec) {
      var secId    = (sec.id    || sec.title || '').trim();
      var secTitle = (sec.title || sec.id    || 'State Jobs').trim();
      var secState = (sec.state || '').trim();
      var items    = Array.isArray(sec.items) ? sec.items : [];

      items.forEach(function(item) {
        var title = (item.name || item.title || '').trim();
        if (!title) return;

        var detail = item.detail || {};
        var bd     = detail.basic_details || {};

        var url = item.url || item.link || '';

        // Prefer internal job.html link built from slug
        var slug = slugifyTitle(bd.job_title || title);
        if (slug) {
          var applyMode = (bd.application_mode || '').toLowerCase();
          var prefix = applyMode.indexOf('offline') !== -1 ? 'offline-' : '';
          url = 'job.html?slug=' + encodeURIComponent(prefix + slug)
              + '&section=' + encodeURIComponent(secId || secTitle);
        }

        if (!url) return;

        var qual = (item.qualification || bd.qualification || '').trim();
        var board = (item.board || bd.organization_name || '').trim();

        addJob({
          title   : title,
          url     : url,
          dept    : board || secTitle,
          post    : '',
          qual    : qual,
          state   : secState || 'All India',
          cat     : 'State Jobs',
          section : secTitle,
          tags    : [title, board, secTitle, secState, qual, bd.short_information].filter(Boolean).join(' '),
        });
        count++;
      });
    });

    console.log('[hero-search] state-jobs-data → ' + count + ' jobs');
  }

  /* ═══════════════════════════════════════════════════════════
     JSON FETCH HELPER
  ═══════════════════════════════════════════════════════════ */
  function fetchJson(file, parser) {
    return fetch(file)
      .then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data) {
        parser(data);
      })
      .catch(function(err) {
        console.warn('[hero-search] Failed:', file, err.message);
      });
  }

  /* ═══════════════════════════════════════════════════════════
     PHASED LOADING
     Phase 1 (fast, ~700KB): merged_sarkari + dailyupdates
     Phase 2 (medium)      : state-jobs-data
     Phase 3 (heavy, ~11MB): Complete_Jobs_Full_Data (delayed 2s)
  ═══════════════════════════════════════════════════════════ */
  function loadData() {
    // Phase 1
    Promise.all([
      fetchJson('merged_sarkari_data.json', parseMergedSarkari),
      fetchJson('dailyupdates.json',        parseDailyUpdates),
    ]).then(function() {
      phase1Ready = true;
      console.log('[hero-search] Phase 1 ready. Total jobs:', allJobs.length);
      refreshActiveSearch();

      // Phase 2
      fetchJson('state-jobs-data.json', parseStateJobs).then(function() {
        console.log('[hero-search] Phase 2 ready. Total jobs:', allJobs.length);
        refreshActiveSearch();
      });
    });

    // Phase 3 — heavy file, 2s delay
    setTimeout(function() {
      fetchJson('Complete_Jobs_Full_Data.json', parseCompleteJobs).then(function() {
        console.log('[hero-search] Phase 3 ready. Total jobs:', allJobs.length);
        refreshActiveSearch();
      });
    }, 2000);
  }

  function refreshActiveSearch() {
    var input = document.getElementById('heroSearch');
    if (input && input.value.trim().length >= 1) {
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  /* ═══════════════════════════════════════════════════════════
     SEARCH ENGINE
     Match against: title, post, dept, cat, qual, state, tags
  ═══════════════════════════════════════════════════════════ */
  var STOP = { 'recruitment':1,'2026':1,'2025':1,'apply':1,'online':1,'offline':1,
               'notification':1,'for':1,'and':1,'the':1,'of':1,'to':1,'in':1,
               'post':1,'grade':1,'form':1,'exam':1,'india':1,'all':1,'latest':1,
               'vacancy':1,'vacancies':1,'jobs':1,'job':1,'new':1,'official':1 };

  function scoreJob(job, q, words, mWords) {
    var title = (job.title  || '').toLowerCase();
    var post  = (job.post   || '').toLowerCase();
    var dept  = (job.dept   || '').toLowerCase();
    var cat   = (job.cat    || '').toLowerCase();
    var qual  = (job.qual   || '').toLowerCase();
    var state = (job.state  || '').toLowerCase();
    var tags  = (job.tags   || '').toLowerCase();
    var score = 0;

    // Exact full query in title
    if (title.indexOf(q) !== -1) score += 200;

    // Meaningful words in title (most weight)
    var titleHits = 0;
    mWords.forEach(function(w) {
      if (title.indexOf(w) !== -1) {
        score += w.length >= 5 ? 40 : 20;
        titleHits++;
      }
    });
    // All meaningful words in title bonus
    if (mWords.length > 0 && titleHits === mWords.length) score += 60;

    // Meaningful words in other fields
    mWords.forEach(function(w) {
      if (post.indexOf(w)  !== -1) score += 18;
      if (dept.indexOf(w)  !== -1) score += 12;
      if (cat.indexOf(w)   !== -1) score += 10;
      if (qual.indexOf(w)  !== -1) score += 10;
      if (state.indexOf(w) !== -1) score += 10;
      if (tags.indexOf(w)  !== -1) score += 8;
    });

    // All query words found in title
    var allHits = 0;
    words.forEach(function(w) { if (title.indexOf(w) !== -1) allHits++; });
    if (words.length >= 2 && allHits === words.length) score += 40;

    return score;
  }

  function search(query) {
    var q      = (query || '').trim().toLowerCase();
    if (q.length < 1) return [];
    var words  = q.split(/\s+/).filter(function(w){ return w.length >= 1; });
    var mWords = words.filter(function(w){ return w.length >= 2 && !STOP[w]; });
    var MIN    = phase1Ready ? 8 : 3;

    var scored = [];
    allJobs.forEach(function(job) {
      var s = scoreJob(job, q, words, mWords);
      if (s >= MIN) scored.push({ job: job, score: s });
    });

    scored.sort(function(a, b) { return b.score - a.score; });
    return scored.map(function(x){ return x.job; });
  }

  /* ═══════════════════════════════════════════════════════════
     CSS INJECTION
  ═══════════════════════════════════════════════════════════ */
  function injectStyles() {
    if (document.getElementById('hs-styles')) return;
    var s = document.createElement('style');
    s.id = 'hs-styles';
    s.textContent = [
      '/* ── Hero Search Dropdown ── */',
      '#hsDrop {',
      '  position:fixed; background:#fff;',
      '  border:1px solid #e2e8f0; border-radius:12px;',
      '  box-shadow:0 16px 48px rgba(13,34,87,.18);',
      '  z-index:99999; max-height:400px; overflow-y:auto;',
      '  display:none;',
      '}',
      '#hsDrop.open { display:block; animation:hsFade .14s ease; }',
      '@keyframes hsFade { from{opacity:0;transform:translateY(-5px)} to{opacity:1;transform:translateY(0)} }',

      '/* ── Suggestion Item ── */',
      '.hs-item {',
      '  display:flex; align-items:center; gap:10px;',
      '  padding:10px 14px; text-decoration:none; color:#0f172a;',
      '  border-bottom:1px solid #f8fafc; transition:background .1s; cursor:pointer;',
      '}',
      '.hs-item:last-of-type { border-bottom:none; }',
      '.hs-item:hover, .hs-item.hs-active { background:#eff6ff; }',
      '.hs-icon {',
      '  width:28px; height:28px; border-radius:7px;',
      '  background:#eff6ff; color:#1a56db;',
      '  display:flex; align-items:center; justify-content:center;',
      '  font-size:.75rem; flex-shrink:0;',
      '}',
      '.hs-body { flex:1; min-width:0; }',
      '.hs-title {',
      '  display:block; font-size:.84rem; font-weight:700;',
      '  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;',
      '  color:#0f172a; line-height:1.3;',
      '}',
      '.hs-item:hover .hs-title, .hs-item.hs-active .hs-title { color:#1a56db; }',
      '.hs-meta {',
      '  font-size:.69rem; color:#64748b; margin-top:2px;',
      '  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;',
      '}',
      '.hs-arr { color:#cbd5e1; font-size:.7rem; flex-shrink:0; }',
      '.hs-item:hover .hs-arr, .hs-item.hs-active .hs-arr { color:#1a56db; }',

      '/* ── Highlight ── */',
      'mark.hs-hl { background:#fef08a; color:#92400e; border-radius:2px; padding:0 1px; font-style:normal; }',

      '/* ── Footer row ── */',
      '.hs-footer {',
      '  display:flex; align-items:center; justify-content:center; gap:6px;',
      '  padding:9px 14px; font-size:.78rem; font-weight:700; color:#1a56db;',
      '  text-decoration:none; border-top:1px solid #f1f5f9; transition:background .12s;',
      '}',
      '.hs-footer:hover { background:#f0f9ff; }',

      '/* ── No results ── */',
      '.hs-empty { padding:14px; font-size:.82rem; color:#94a3b8; text-align:center; }',

      '/* ── Recent row ── */',
      '.hs-recent { padding:8px 14px; border-bottom:1px solid #f1f5f9; }',
      '.hs-recent-hd { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; font-size:.7rem; font-weight:800; color:#475569; }',
      '.hs-clear-btn { background:none; border:1px solid #e2e8f0; border-radius:5px; padding:2px 7px; font-size:.67rem; color:#94a3b8; cursor:pointer; font-family:inherit; }',
      '.hs-clear-btn:hover { color:#ef4444; border-color:#ef4444; }',
      '.hs-recent-tags { display:flex; flex-wrap:wrap; gap:5px; }',
      '.hs-rtag {',
      '  background:#f8fafc; color:#475569; border:1px solid #e2e8f0;',
      '  border-radius:6px; padding:3px 9px; font-size:.71rem; font-weight:600;',
      '  cursor:pointer; font-family:inherit; transition:all .12s;',
      '}',
      '.hs-rtag:hover { background:#eff6ff; color:#1a56db; border-color:#bfdbfe; }',
    ].join('\n');
    document.head.appendChild(s);
  }

  /* ═══════════════════════════════════════════════════════════
     DROPDOWN RENDER
  ═══════════════════════════════════════════════════════════ */
  function renderItem(job, q, idx) {
    var active = idx === activeIdx ? ' hs-active' : '';
    // Determine icon based on category
    var iconMap = {
      'railway jobs'  : 'fa-train',
      'bank jobs'     : 'fa-building-columns',
      'police jobs'   : 'fa-shield-halved',
      'defence jobs'  : 'fa-star',
      'teaching jobs' : 'fa-chalkboard-user',
      'admit card'    : 'fa-id-card',
      'result'        : 'fa-trophy',
      'state jobs'    : 'fa-location-dot',
      'answer key'    : 'fa-key',
      'admission'     : 'fa-graduation-cap',
      'psu jobs'      : 'fa-industry',
      'medical jobs'  : 'fa-stethoscope',
      'iti jobs'      : 'fa-tools',
    };
    var catKey = (job.cat || '').toLowerCase();
    var icon = iconMap[catKey] || 'fa-briefcase';

    // Meta: show dept + state if available
    var metaParts = [];
    if (job.section || job.cat) metaParts.push(esc(job.section || job.cat));
    if (job.state && job.state !== 'All India') metaParts.push(esc(job.state));
    var meta = metaParts.join(' · ');

    return '<a class="hs-item' + active + '" href="' + esc(job.url) + '" data-idx="' + idx + '">' +
      '<span class="hs-icon"><i class="fa-solid ' + esc(icon) + '"></i></span>' +
      '<span class="hs-body">' +
        '<span class="hs-title">' + highlight(job.title, q) + '</span>' +
        (meta ? '<span class="hs-meta">' + meta + '</span>' : '') +
      '</span>' +
      '<span class="hs-arr"><i class="fa-solid fa-arrow-right"></i></span>' +
    '</a>';
  }

  function renderRecent() {
    var recent = getRecent();
    if (!recent.length) return '';
    return '<div class="hs-recent">' +
      '<div class="hs-recent-hd">' +
        '<span><i class="fa-solid fa-clock-rotate-left"></i> Recent</span>' +
        '<button class="hs-clear-btn" id="hsClearRecent">Clear</button>' +
      '</div>' +
      '<div class="hs-recent-tags">' +
        recent.map(function(r) {
          return '<button class="hs-rtag" data-q="' + esc(r) + '">' + esc(r) + '</button>';
        }).join('') +
      '</div>' +
    '</div>';
  }

  /* ═══════════════════════════════════════════════════════════
     HERO SEARCH SETUP
  ═══════════════════════════════════════════════════════════ */
  function setup() {
    var input = document.getElementById('heroSearch');
    var btn   = document.getElementById('heroSearchBtn');
    if (!input) return;

    injectStyles();

    /* Create dropdown */
    var drop = document.createElement('div');
    drop.id = 'hsDrop';
    drop.setAttribute('role', 'listbox');
    document.body.appendChild(drop);

    /* Position dropdown under search box */
    function pos() {
      var box  = input.closest('.hero-search-box') || input;
      var rect = box.getBoundingClientRect();
      drop.style.top    = (rect.bottom + 5) + 'px';
      drop.style.left   = rect.left + 'px';
      drop.style.width  = rect.width + 'px';
    }
    pos();
    window.addEventListener('resize', function() { if (drop.classList.contains('open')) pos(); });
    window.addEventListener('scroll', function() { if (drop.classList.contains('open')) pos(); }, true);

    /* Open/close helpers */
    function openDrop(html) {
      pos();
      drop.innerHTML = html;
      drop.classList.add('open');
      wireEvents();
    }
    function closeDrop() {
      drop.classList.remove('open');
      drop.innerHTML = '';
      activeIdx = -1;
      suggestList = [];
    }

    /* Wire events inside dropdown (recent tags, clear) */
    function wireEvents() {
      drop.querySelectorAll('.hs-rtag').forEach(function(b) {
        b.addEventListener('click', function() {
          input.value = b.dataset.q;
          runSearch(b.dataset.q);
        });
      });
      var clearBtn = drop.querySelector('#hsClearRecent');
      if (clearBtn) {
        clearBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          try { localStorage.removeItem(CFG.recentKey); } catch(e) {}
          openDrop('<div class="hs-empty">Type to search jobs…</div>');
        });
      }
    }

    /* Show suggestions for a query */
    function runSearch(q) {
      q = (q || '').trim();
      if (!q) {
        var recentHtml = renderRecent();
        openDrop(recentHtml || '<div class="hs-empty">Type to search jobs…</div>');
        return;
      }

      var results = search(q).slice(0, CFG.maxSuggest);
      activeIdx   = -1;
      suggestList = results;

      var html;
      if (!results.length) {
        html = '<div class="hs-empty">No results for "<strong>' + esc(q) + '</strong>".<br>Try: SSC · Railway · Bank · Police · Army</div>';
      } else {
        html = results.map(function(job, i){ return renderItem(job, q, i); }).join('');
        html += '<a class="hs-footer" href="search.html?q=' + encodeURIComponent(q) + '">'
              + '<i class="fa-solid fa-magnifying-glass"></i> See all results for &ldquo;' + esc(q) + '&rdquo;'
              + '</a>';
      }
      openDrop(html);
    }

    /* Keyboard navigation */
    function navigate(dir) {
      var items = drop.querySelectorAll('.hs-item');
      if (!items.length) return;
      activeIdx += dir;
      if (activeIdx < 0) activeIdx = items.length - 1;
      if (activeIdx >= items.length) activeIdx = 0;
      items.forEach(function(el, i) {
        el.classList.toggle('hs-active', i === activeIdx);
      });
    }

    /* ── Input events ── */
    var debouncedSearch = debounce(function() {
      runSearch(input.value);
    }, CFG.debounceMs);

    input.addEventListener('input',   debouncedSearch);
    input.addEventListener('focus',   function() {
      if (!input.value.trim()) {
        var recentHtml = renderRecent();
        openDrop(recentHtml || '<div class="hs-empty">Type to search jobs…</div>');
      } else {
        runSearch(input.value);
      }
    });

    input.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowDown')  { e.preventDefault(); navigate(1); }
      if (e.key === 'ArrowUp')    { e.preventDefault(); navigate(-1); }
      if (e.key === 'Escape')     { closeDrop(); input.blur(); }
      if (e.key === 'Enter') {
        e.preventDefault();
        var active = drop.querySelector('.hs-item.hs-active');
        if (active) {
          saveRecent(input.value.trim());
          window.location.href = active.href;
        } else if (input.value.trim()) {
          saveRecent(input.value.trim());
          window.location.href = 'search.html?q=' + encodeURIComponent(input.value.trim());
        }
      }
    });

    /* ── Search button ── */
    if (btn) {
      btn.addEventListener('click', function() {
        var q = input.value.trim();
        if (!q) return;
        saveRecent(q);
        closeDrop();
        window.location.href = 'search.html?q=' + encodeURIComponent(q);
      });
    }

    /* ── Click on dropdown item — save recent ── */
    drop.addEventListener('click', function(e) {
      var item = e.target.closest('.hs-item');
      if (item) {
        saveRecent(input.value.trim());
        closeDrop();
        // navigation handled by href
      }
    });

    /* ── Click outside — close ── */
    document.addEventListener('click', function(e) {
      var box = input.closest('.hero-search-box') || input.parentElement;
      if (!drop.contains(e.target) && !box.contains(e.target)) {
        closeDrop();
      }
    });
  }

  /* ═══════════════════════════════════════════════════════════
     INIT
  ═══════════════════════════════════════════════════════════ */
  function init() {
    setup();    // UI setup first
    loadData(); // then fetch JSON data in background
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
