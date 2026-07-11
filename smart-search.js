/**
 * ============================================================
 * TOP SARKARI JOBS – INTELLIGENT PRIORITY SEARCH v4.0
 * ============================================================
 * PRIORITY SYSTEM:
 *   P1 (1000+) — Exact Job Title Match → Job Detail Page
 *   P2 (600+)  — All Query Words in Title → Job Detail Page
 *   P3 (400+)  — Partial Title Match (60%+ words) → Job Detail
 *   P4 (200+)  — SEO Tags / Organization / Post Name Match
 *   P5 (100+)  — Category / Section / State Page
 *   P6 (<100)  — Generic / Unrelated
 *
 * QUERY TYPE DETECTION:
 *   SPECIFIC → "SSC GD", "Haryana Police" → Job Detail Pages First
 *   GENERAL  → "10th Pass", "Admit Card"  → Category/Section Pages
 *
 * DATA SOURCES (Auto-detected):
 *   Complete_Jobs_Full_Data.json sarkari_data — LATEST_JOBS NEW, STATE_JOBS etc
 *   Complete_Jobs_Full_Data.json — qualification-wise jobs
 *   Complete_Jobs_Full_Data.json state_jobs — state-wise jobs
 *   Complete_Jobs_Full_Data.json education_jobs — education/exam entries
 *   dailyupdates.json — daily updates
 * ============================================================
 */
(function () {
  'use strict';

  /* ══════════════════════════════════════════════════════════
   * CONFIG
   * ══════════════════════════════════════════════════════════ */
  var CFG = {
    maxSuggest: 10,
    debounceMs: 120,
    recentKey: 'tsj_recent_v4',
    maxRecent: 8,
    refreshIntervalMs: 15 * 60 * 1000,
  };

  /* ══════════════════════════════════════════════════════════
   * QUERY TYPE DETECTION
   * Determines whether query is SPECIFIC (job search) or
   * GENERAL (category/qualification/section search)
   * ══════════════════════════════════════════════════════════ */
  var GENERAL_KEYWORDS = {
    '10th':1,'10th pass':1,'tenth':1,'matric':1,
    '12th':1,'12th pass':1,'intermediate':1,'inter':1,
    '8th':1,'8th pass':1,'eighth':1,
    'graduate':1,'graduation':1,'degree':1,'any graduate':1,
    'diploma':1,'iti':1,'btech':1,'b.tech':1,'mba':1,'mca':1,'bca':1,
    'post graduate':1,'pg':1,'m.sc':1,'m.a':1,'m.com':1,
    'admit card':1,'admit':1,'hall ticket':1,'call letter':1,
    'result':1,'results':1,'merit list':1,'cut off':1,'cutoff':1,
    'answer key':1,'answer sheet':1,'objection':1,
    'admission':1,'counselling':1,'counseling':1,
    'sarkari result':1,'sarkari naukri':1,'govt job':1,'government job':1,
    'haryana jobs':1,'up jobs':1,'rajasthan jobs':1,'bihar jobs':1,
    'state jobs':1,'central jobs':1,'upcoming jobs':1,'offline form':1,
    'latest jobs':1,'new jobs':1,'today jobs':1,
    'scheme':1,'yojna':1,'yojana':1,'pm scheme':1,
  };

  var SPECIFIC_PATTERNS = [
    /\b(ssc|upsc|rrb|rrc|rpf|bsf|crpf|cisf|ssb|itbp|nda|cds|afcat)\b/i,
    /\b(constable|si|sub inspector|inspector|aso|mts|chsl|cgl|cpo|je|ae)\b/i,
    /\b(railway|airforce|navy|army|paramilitary|police|ntpc|group.?d|group.?c)\b/i,
    /\b(aiims|pgi|esic|nhi|cghs|drdo|isro|barc|hal|bhel|ongc|sail|bel)\b/i,
    /\b(clerk|steno|typist|accountant|assistant|officer|engineer|technician)\b/i,
    /\b(teacher|pgt|tgt|prt|lecturer|professor|principal|head master)\b/i,
    /\b(bank|ibps|sbi|rbi|nabard|po|so|probationary)\b/i,
    /\b(haryana police|haryana staff|hssc|hpsc|htet|hptet)\b/i,
    /\b(vacancy|recruitment|bharti|notification|post|posts)\b/i,
  ];

  function detectQueryType(q) {
    var lower = q.toLowerCase().trim();
    // Check general keywords first
    if (GENERAL_KEYWORDS[lower]) return 'GENERAL';
    var words = lower.split(/\s+/);
    if (words.length === 1) {
      var w = words[0];
      if (GENERAL_KEYWORDS[w]) return 'GENERAL';
      if (/^(admit|result|answer|scheme|yojna|offline|upcoming|latest|state|central)$/i.test(w)) return 'GENERAL';
      if (/^(10th|12th|8th|iti|diploma|btech|graduate|pg|mba)$/i.test(w)) return 'GENERAL';
    }
    // Check specific patterns
    for (var i = 0; i < SPECIFIC_PATTERNS.length; i++) {
      if (SPECIFIC_PATTERNS[i].test(lower)) return 'SPECIFIC';
    }
    // Multi-word with state + keyword = SPECIFIC (e.g. "Haryana Police")
    if (words.length >= 2) {
      var stateWords = ['haryana','delhi','punjab','rajasthan','bihar','up','gujarat','maharashtra',
                        'karnataka','tamil','kerala','bengal','assam','odisha','jharkhand',
                        'chhattisgarh','uttarakhand','himachal','jammu','kashmir','mp','andhra',
                        'telangana','manipur','meghalaya','sikkim','tripura','nagaland','mizoram'];
      var hasState = stateWords.some(function(s){ return lower.indexOf(s) !== -1; });
      var hasJobWord = /constable|police|patwari|teacher|clerk|engineer|nurse|driver|guard|peon|conductor|instructor/i.test(lower);
      if (hasState && hasJobWord) return 'SPECIFIC';
    }
    // Default: if query >= 3 chars and not matching general → treat as SPECIFIC
    return q.length >= 3 ? 'SPECIFIC' : 'GENERAL';
  }

  /* ══════════════════════════════════════════════════════════
   * STOP WORDS — removed from scoring to avoid noise
   * ══════════════════════════════════════════════════════════ */
  var STOP = {
    'recruitment':1,'2026':1,'2025':1,'2024':1,'apply':1,'online':1,'offline':1,
    'now':1,'out':1,'notification':1,'for':1,'and':1,'the':1,'of':1,'to':1,
    'in':1,'a':1,'an':1,'is':1,'are':1,'with':1,'posts':1,'post':1,'grade':1,
    'form':1,'exam':1,'test':1,'board':1,'india':1,'all':1,'bharti':1,
    'vacancy':1,'vacancies':1,'latest':1,'new':1,'official':1,'download':1,
    'check':1,'full':1,'details':1,'info':1,'information':1,'released':1,
    'notification':1,'sarkari':1,'naukri':1,'free':1,'link':1,
  };

  /* ══════════════════════════════════════════════════════════
   * SCORING ENGINE — Priority-based
   * ══════════════════════════════════════════════════════════ */
  function scoreItem(item, q, queryWords, meaningfulWords, qType) {
    var title  = (item.title  || '').toLowerCase();
    var tags   = (item.tags   || '').toLowerCase();
    var dept   = (item.dept   || '').toLowerCase();
    var cat    = (item.cat    || '').toLowerCase();
    var sec    = (item.sectionSource || '').toLowerCase();
    var state  = (item.state  || '').toLowerCase();
    var postN  = (item.postName || '').toLowerCase();
    var isJobDetail = item.isJobDetail === true;
    var score  = 0;

    /* ── P1: EXACT TITLE MATCH (highest priority) ── */
    if (title === q) {
      score += 1500;
    } else if (title.indexOf(q) === 0) {
      /* Title starts with exact query */
      score += 1000;
    } else if (title.indexOf(q) !== -1) {
      /* Title contains exact query substring */
      score += 600;
    }

    /* ── P2: ALL meaningful words in title ── */
    if (meaningfulWords.length >= 1) {
      var titleWordHits = meaningfulWords.filter(function(w){ return title.indexOf(w) !== -1; });
      var hitRatio = titleWordHits.length / meaningfulWords.length;

      if (hitRatio === 1 && meaningfulWords.length >= 2) {
        score += 400; // ALL words match
      } else if (hitRatio >= 0.75) {
        score += 200;
      } else if (hitRatio >= 0.5) {
        score += 100;
      }

      /* Word-length weighted scoring */
      titleWordHits.forEach(function(w) {
        if (w.length >= 6) score += 50;
        else if (w.length >= 4) score += 30;
        else score += 15;
      });
    }

    /* ── P3: EXACT FIRST WORD MATCH (title starts with query word) ── */
    if (queryWords.length > 0 && title.indexOf(queryWords[0]) === 0) {
      score += 80;
    }

    /* ── P4: SEO TAGS exact match (very high value) ── */
    if (item.seoTags) {
      var seoArr = Array.isArray(item.seoTags) ? item.seoTags : [item.seoTags];
      seoArr.forEach(function(tag) {
        var t = (tag || '').toLowerCase();
        if (t === q) score += 500;
        else if (t.indexOf(q) !== -1) score += 200;
        else {
          meaningfulWords.forEach(function(w) {
            if (t.indexOf(w) !== -1) score += 60;
          });
        }
      });
    }

    /* ── P5: Organization / Post Name match ── */
    if (dept) {
      if (dept.indexOf(q) !== -1) score += 250;
      else meaningfulWords.forEach(function(w){ if (dept.indexOf(w) !== -1) score += 40; });
    }
    if (postN) {
      if (postN.indexOf(q) !== -1) score += 200;
      else meaningfulWords.forEach(function(w){ if (postN.indexOf(w) !== -1) score += 35; });
    }

    /* ── P6: Tags / Category / State ── */
    meaningfulWords.forEach(function(w) {
      if (tags.indexOf(w)  !== -1) score += w.length >= 5 ? 20 : 10;
      if (cat.indexOf(w)   !== -1) score += 8;
      if (sec.indexOf(w)   !== -1) score += 6;
      if (state.indexOf(w) !== -1) score += 12; // State is useful
    });

    /* ── QUERY TYPE MODIFIERS ── */
    if (qType === 'SPECIFIC') {
      /* For specific queries: massively boost job detail pages */
      if (isJobDetail) score = Math.round(score * 1.8);
      /* Penalize category/section pages in specific searches */
      if (item.isCategory || item.isSection) score = Math.round(score * 0.3);
    } else {
      /* For general queries: boost category/section pages */
      if (item.isCategory || item.isSection) score = Math.round(score * 1.5);
      if (isJobDetail) score = Math.round(score * 0.7);
    }

    /* ── RECENCY BOOST ── */
    if (score > 0 && item.lastUpdated) {
      try {
        var diffDays = (Date.now() - new Date(item.lastUpdated).getTime()) / 86400000;
        if (diffDays <= 1)  score += 50;
        else if (diffDays <= 3)  score += 30;
        else if (diffDays <= 7)  score += 15;
        else if (diffDays <= 30) score += 5;
      } catch(e) {}
    }

    /* ── ACTIVE JOB BOOST (has future last date) ── */
    if (score > 0 && item.lastDate) {
      try {
        var parts = item.lastDate.split(/[\/\-]/);
        var ld;
        if (parts[2] && parts[2].length === 4) {
          ld = new Date(parts[2] + '-' + parts[1] + '-' + parts[0]);
        } else {
          ld = new Date(item.lastDate);
        }
        if (!isNaN(ld.getTime()) && ld > Date.now()) score += 40;
      } catch(e) {}
    }

    return score;
  }

  /* ══════════════════════════════════════════════════════════
   * STATE
   * ══════════════════════════════════════════════════════════ */
  var allData     = [];
  var activeIndex = -1;
  var suggestItems = [];
  var searchReady = false;
  var lastJsonHashes = {};

  /* ══════════════════════════════════════════════════════════
   * UTILS
   * ══════════════════════════════════════════════════════════ */
  function esc(s) {
    return String(s || '').replace(/[&<>"]/g, function(c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }

  function debounce(fn, ms) {
    var t, ctx = this;
    return function() {
      var args = arguments;
      clearTimeout(t);
      t = setTimeout(function(){ fn.apply(ctx, args); }, ms);
    };
  }

  function highlight(text, query) {
    if (!text || !query) return esc(text);
    var words = query.trim().split(/\s+/).filter(function(w){ return w.length > 1; });
    var out = esc(text);
    words.forEach(function(w) {
      var re = new RegExp('(' + w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + ')', 'gi');
      out = out.replace(re, '<mark class="srch-hl">$1</mark>');
    });
    return out;
  }

  function slugifyTitle(raw) {
    return (raw || '').toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/[\s-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0,80).replace(/-+$/,"");
  }

  // Prefer the generator's disk-truth canonical slug (the exact /jobs/<dir>/ that
  // was actually built). Slugifying the title as a fallback would invent URLs
  // like /jobs/haryana-rte-admission-online-form-2026/ that 404 — the real page
  // uses a trimmed canonical slug (haryana-rte-admission-2026). NEVER trust a raw
  // `slug` field over `_canonical_slug`: legacy `slug` values can be stale.
  function canonicalSlug(obj, title) {
    var c = obj && (obj._canonical_slug || obj.canonical_slug || obj.canonicalSlug);
    c = String(c || '').trim().replace(/^\/+|\/+$/g, '').replace(/^jobs\//, '').replace(/\/+$/, '');
    if (c) return c;
    return slugifyTitle(title || '');
  }

  /* ══════════════════════════════════════════════════════════
   * DISK-TRUTH URL RESOLVER — never emit a /jobs/ URL that 404s.
   * jobs-index.json is keyed by the EXACT on-disk slug of every built job page.
   * We resolve each result to a REAL key via: canonical → slugified-title →
   * exact-title → fuzzy-title. If nothing matches, the item has no page and is
   * skipped (so the hero search only ever opens pages that actually exist).
   * ══════════════════════════════════════════════════════════ */
  var JOB_INDEX = { slugs: null, title2slug: null, ready: false };
  function normTitle(t) {
    return String(t || '').toLowerCase().replace(/&amp;/g, '&')
      .replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' ');
  }
  var jobIndexPromise = fetch('/jobs-index.json', { cache: 'default' })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(idx) {
      if (!idx || typeof idx !== 'object') return;
      JOB_INDEX.slugs = Object.create(null);
      JOB_INDEX.title2slug = Object.create(null);
      Object.keys(idx).forEach(function(slug) {
        JOB_INDEX.slugs[slug] = 1;
        var t = normTitle(idx[slug] && idx[slug].title);
        if (t && !JOB_INDEX.title2slug[t]) JOB_INDEX.title2slug[t] = slug;
      });
      JOB_INDEX.ready = true;
    })
    .catch(function() {});

  // Return a REAL '/jobs/<slug>/' URL for this item, or '' if no page exists.
  // Only RELIABLE matches are used (canonical slug → slugified title → exact
  // normalized title, all checked against the disk-truth index). Fuzzy matching
  // was deliberately dropped — it linked near-duplicate titles to the WRONG job
  // (e.g. "Technician CEN 02" → "Section Controller CEN 03"). An item that
  // matches none of these has no built page and is skipped (never a 404, never
  // a wrong page).
  function resolveJobUrl(canonical, title) {
    var S = JOB_INDEX.slugs;
    canonical = String(canonical || '').trim().replace(/^\/+|\/+$/g, '').replace(/^jobs\//, '').replace(/\/+$/, '');
    if (!S) {                                  // index not loaded yet — best effort
      var f = canonical || slugifyTitle(title);
      return f ? '/jobs/' + f + '/' : '';
    }
    if (canonical && S[canonical]) return '/jobs/' + canonical + '/';
    var sfy = slugifyTitle(title);
    if (sfy && S[sfy]) return '/jobs/' + sfy + '/';
    var nt = normTitle(title);
    if (JOB_INDEX.title2slug[nt]) return '/jobs/' + JOB_INDEX.title2slug[nt] + '/';
    return '';
  }

  function getRecent() {
    try { return JSON.parse(localStorage.getItem(CFG.recentKey) || '[]'); } catch(e) { return []; }
  }

  function saveRecent(q) {
    if (!q || q.length < 2) return;
    var list = getRecent().filter(function(r){ return r.toLowerCase() !== q.toLowerCase(); });
    list.unshift(q);
    try { localStorage.setItem(CFG.recentKey, JSON.stringify(list.slice(0, CFG.maxRecent))); } catch(e) {}
  }

  function dedupeKey(slug) {
    if (!slug) return '';
    try {
      var u = new URL(slug, 'https://x.com');
      return (u.searchParams.get('slug') || u.pathname).toLowerCase().trim();
    } catch(e) {
      return slug.split('?')[0].toLowerCase().trim();
    }
  }

  function quickHash(data) {
    var str = JSON.stringify(data).slice(0, 8000);
    var h = 0;
    for (var i = 0; i < str.length; i++) {
      h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
    }
    return h;
  }

  /* ══════════════════════════════════════════════════════════
   * URL BUILDER
   * ══════════════════════════════════════════════════════════ */
  function buildJobUrl(title, applyMode, secId) {
    var slug = slugifyTitle(title);
    if (!slug || slug === 'official-link') return null;
    var prefix = (applyMode || '').toLowerCase() === 'offline' ? 'offline-' : '';
    var url = '/jobs/' + prefix + slug + '/';
    return url;
  }

  function buildJobHref(job, secId) {
    var bd = job.basic_details || {};
    var rawTitle = job.title || job.post_name || bd.job_title || bd.post_name || '';
    var canon = job._canonical_slug || job.canonical_slug || '';
    if (canon) return '/jobs/' + String(canon).replace(/^\/+|\/+$/g,'').replace(/^jobs\//,'').replace(/\/+$/,'') + '/';
    var slug = job.slug || slugifyTitle(rawTitle);
    if (!slug || slug === 'official-link') return job.source_url || job.url || job.link || '#';
    var applyMode = (job.apply_mode || bd.application_mode || '').toLowerCase();
    var prefix = applyMode === 'offline' ? 'offline-' : '';
    return '/jobs/' + prefix + slug + '/';
  }

  function getJobTitle(job) {
    var bd = job.basic_details || {};
    return String(
      job.title || job.post_name || bd.job_title || bd.post_name || job.name || ''
    ).trim().replace(/[\s\-\u2013\u2014,|]+$/, '').trim();
  }

  function getJobOrg(job) {
    var bd = job.basic_details || {};
    return String(
      job.organization || job.board_name || job.department ||
      bd.organization_name || bd.department || ''
    ).trim();
  }

  /* ══════════════════════════════════════════════════════════
   * MERGE INTO allData (dedup)
   * ══════════════════════════════════════════════════════════ */
  function mergeItems(extra) {
    if (!extra || !extra.length) return false;
    var seen = {};
    allData.forEach(function(d){ seen[dedupeKey(d.slug)] = true; });
    var added = 0;
    extra.forEach(function(item) {
      if (!item.title || !item.slug) return;
      var key = dedupeKey(item.slug);
      if (!seen[key]) {
        seen[key] = true;
        if (!item.lastUpdated) item.lastUpdated = new Date().toISOString();
        allData.push(item);
        added++;
      }
    });
    return added > 0;
  }

  /* ══════════════════════════════════════════════════════════
   * CATEGORY / SECTION PAGES (General query targets)
   * ══════════════════════════════════════════════════════════ */
  var CAT_PAGES = [
    { title:'10th Pass Jobs 2026', slug:'/section/10th-pass-jobs/', cat:'Qualification', tags:'10th pass matric 10 tenth class pass sarkari job', icon:'fa-certificate', isCategory:true, isSection:true, state:'All India' },
    { title:'12th Pass Jobs 2026', slug:'/section/12th-pass-jobs/', cat:'Qualification', tags:'12th pass intermediate inter 12 class pass sarkari', icon:'fa-certificate', isCategory:true, isSection:true, state:'All India' },
    { title:'8th Pass Jobs 2026', slug:'/section/8th-pass-jobs/', cat:'Qualification', tags:'8th pass eighth 8 class pass sarkari job', icon:'fa-certificate', isCategory:true, isSection:true, state:'All India' },
    { title:'ITI Pass Jobs 2026', slug:'/section/iti-jobs/', cat:'Qualification', tags:'iti pass diploma technical trade vocational', icon:'fa-tools', isCategory:true, isSection:true, state:'All India' },
    { title:'Diploma Jobs 2026', slug:'/section/diploma-jobs/', cat:'Qualification', tags:'diploma polytechnic technical engineering pass', icon:'fa-scroll', isCategory:true, isSection:true, state:'All India' },
    { title:'Graduate Jobs 2026', slug:'/section/graduation-jobs/', cat:'Qualification', tags:'graduate graduation degree any graduate bsc ba bcom', icon:'fa-graduation-cap', isCategory:true, isSection:true, state:'All India' },
    { title:'Post Graduate Jobs 2026', slug:'/section/post-graduation-jobs/', cat:'Qualification', tags:'post graduate pg msc ma mcom mba mca masters degree', icon:'fa-graduation-cap', isCategory:true, isSection:true, state:'All India' },
    { title:'B.Tech / BE Jobs 2026', slug:'/section/btech-jobs/', cat:'Qualification', tags:'btech be engineering b.tech b.e technical degree', icon:'fa-microchip', isCategory:true, isSection:true, state:'All India' },
    { title:'Admit Card 2026', slug:'/section/admit-card/', cat:'Admit Card', tags:'admit card hall ticket call letter download exam', icon:'fa-id-card', isCategory:true, isSection:true, state:'All India' },
    { title:'Results 2026', slug:'/section/results/', cat:'Result', tags:'result merit list cut off cutoff scorecard declared', icon:'fa-trophy', isCategory:true, isSection:true, state:'All India' },
    { title:'Answer Key 2026', slug:'/section/answer-key/', cat:'Answer Key', tags:'answer key sheet objection challenge download pdf', icon:'fa-key', isCategory:true, isSection:true, state:'All India' },
    { title:'Admission / Counselling 2026', slug:'/section/admissions/', cat:'Admission', tags:'admission counselling counseling form apply college university', icon:'fa-graduation-cap', isCategory:true, isSection:true, state:'All India' },
    { title:'Railway Jobs 2026', slug:'/section/railway-jobs/', cat:'Railway', tags:'railway rrb rrc ntpc group d c technician loco pilot station master', icon:'fa-train', isCategory:true, isSection:true, state:'All India' },
    { title:'Bank Jobs 2026', slug:'/section/bank-jobs/', cat:'Bank', tags:'bank sbi ibps rbi nabard po clerk so probationary officer', icon:'fa-building-columns', isCategory:true, isSection:true, state:'All India' },
    { title:'Police Jobs 2026', slug:'/section/police-jobs/', cat:'Police', tags:'police constable si sub inspector inspector crpf bsf cisf ssb rpf', icon:'fa-shield-halved', isCategory:true, isSection:true, state:'All India' },
    { title:'Army / Defence Jobs 2026', slug:'/section/army-jobs/', cat:'Defence', tags:'army navy airforce defence nda cds afcat soldier soldier recruitment', icon:'fa-star', isCategory:true, isSection:true, state:'All India' },
    { title:'Teaching Jobs 2026', slug:'/section/teaching-jobs/', cat:'Teaching', tags:'teacher pgt tgt prt lecturer professor principal hm headmaster tet ctet', icon:'fa-chalkboard-user', isCategory:true, isSection:true, state:'All India' },
    { title:'Medical / Healthcare Jobs 2026', slug:'/section/healthcare-jobs/', cat:'Medical', tags:'medical nurse doctor aiims esic cghs pgi hospital health pharmacy lab', icon:'fa-stethoscope', isCategory:true, isSection:true, state:'All India' },
    { title:'SSC Jobs 2026', slug:'/section/ssc-jobs/', cat:'SSC', tags:'ssc cgl chsl mts cpo je gd constable stenographer exam', icon:'fa-medal', isCategory:true, isSection:true, state:'All India' },
    { title:'UPSC Jobs 2026', slug:'/section/upsc-jobs/', cat:'UPSC', tags:'upsc ias ips ifs civil services combined medical engineering exam', icon:'fa-landmark', isCategory:true, isSection:true, state:'All India' },
    { title:'State Jobs 2026', slug:'/section/state-jobs/', cat:'State', tags:'state government haryana delhi punjab rajasthan bihar up mp jobs', icon:'fa-map-location-dot', isCategory:true, isSection:true, state:'All India' },
    { title:'Central Government Jobs 2026', slug:'/section/central-jobs/', cat:'Central', tags:'central government psu public sector bank railway defence ministry', icon:'fa-flag', isCategory:true, isSection:true, state:'All India' },
    { title:'Upcoming Jobs 2026', slug:'/section/upcoming-jobs/', cat:'Upcoming', tags:'upcoming jobs future notification coming soon expected calendar', icon:'fa-calendar-plus', isCategory:true, isSection:true, state:'All India' },
    { title:'Offline Form Jobs 2026', slug:'/section/offline-form/', cat:'Offline', tags:'offline form application send post district recruitment', icon:'fa-file-pen', isCategory:true, isSection:true, state:'All India' },
    { title:'Latest Jobs New 2026', slug:'/section/latest-jobs-new/', cat:'Latest Jobs', tags:'latest new jobs 2026 today recent notification', icon:'fa-fire', isCategory:true, isSection:true, state:'All India' },
    { title:'Latest Government Jobs 2026', slug:'/section/latest-jobs/', cat:'Latest Jobs', tags:'latest government sarkari naukri jobs 2026 today', icon:'fa-briefcase', isCategory:true, isSection:true, state:'All India' },
    { title:'Haryana Jobs 2026', slug:'/section/haryana-all-state-jobs/', cat:'State', tags:'haryana jobs hpsc hssc htet haryana police patwari haryana govt', icon:'fa-location-dot', isCategory:true, isSection:true, state:'Haryana' },
    { title:'CBSE / ICSE 10th Board Result 2026', slug:'/education-detail.html?section=cbse-icse-10th', cat:'Education', tags:'cbse icse 10th board result class 10 matric result', icon:'fa-book-open', isCategory:true, state:'All India' },
    { title:'CBSE / ICSE 12th Board Result 2026', slug:'/education-detail.html?section=cbse-icse-12th', cat:'Education', tags:'cbse icse 12th board result class 12 intermediate result', icon:'fa-graduation-cap', isCategory:true, state:'All India' },
    { title:'GATE / JEE Engineering Exam', slug:'/education-detail.html?section=all-india-engineering', cat:'Education', tags:'gate jee engineering entrance exam iit nit admission', icon:'fa-microchip', isCategory:true, state:'All India' },
    { title:'NEET / AIIMS Medical Entrance', slug:'/education-detail.html?section=all-india-medical', cat:'Education', tags:'neet aiims medical entrance exam mbbs bds admission', icon:'fa-stethoscope', isCategory:true, state:'All India' },
    { title:'CAT / MAT Management Entrance', slug:'/education-detail.html?section=all-india-management', cat:'Education', tags:'cat mat xat management mba entrance exam iim', icon:'fa-chart-line', isCategory:true, state:'All India' },
  ];

  /* ══════════════════════════════════════════════════════════
   * COMPLETE_JOBS META — qualification-wise categories
   * ══════════════════════════════════════════════════════════ */
  var COMPLETE_JOBS_META = {
    '10TH_Pass':            { id:'10th-pass-jobs',       cat:'10th Pass',       qual:'10th Pass',          icon:'fa-certificate',       label:'10th Pass Jobs' },
    '8TH_Pass':             { id:'8th-pass-jobs',        cat:'8th Pass',        qual:'8th Pass',           icon:'fa-certificate',       label:'8th Pass Jobs' },
    '12TH_Pass':            { id:'12th-pass-jobs',       cat:'12th Pass',       qual:'12th Pass',          icon:'fa-certificate',       label:'12th Pass Jobs' },
    'Diploma':              { id:'diploma-jobs',         cat:'Diploma',         qual:'Diploma',            icon:'fa-scroll',            label:'Diploma Jobs' },
    'ITI':                  { id:'iti-jobs',             cat:'ITI',             qual:'ITI',                icon:'fa-tools',             label:'ITI Jobs' },
    'B_Tech_BE':            { id:'btech-jobs',           cat:'B.Tech/BE',       qual:'B.Tech/BE',          icon:'fa-microchip',         label:'B.Tech Jobs' },
    'B_Com':                { id:'bcom-jobs',            cat:'B.Com',           qual:'B.Com',              icon:'fa-calculator',        label:'B.Com Jobs' },
    'Any_Graduate':         { id:'graduation-jobs',      cat:'Graduate',        qual:'Any Graduate',       icon:'fa-graduation-cap',    label:'Graduate Jobs' },
    'Any_Post_Graduate':    { id:'post-graduation-jobs', cat:'Post Graduate',   qual:'Post Graduate',      icon:'fa-graduation-cap',    label:'PG Jobs' },
    'Railway_Jobs':         { id:'railway-jobs',         cat:'Railway',         qual:'',                   icon:'fa-train',             label:'Railway Jobs' },
    'Police_Defence':       { id:'police-jobs',          cat:'Police/Defence',  qual:'',                   icon:'fa-shield-halved',     label:'Police Jobs' },
    'Teaching_Faculty':     { id:'teaching-jobs',        cat:'Teaching',        qual:'',                   icon:'fa-chalkboard-user',   label:'Teaching Jobs' },
    'Bank_Jobs':            { id:'bank-jobs',            cat:'Bank',            qual:'',                   icon:'fa-building-columns',  label:'Bank Jobs' },
    'Medical_Hospital':     { id:'healthcare-jobs',      cat:'Medical',         qual:'',                   icon:'fa-stethoscope',       label:'Medical Jobs' },
    'Latest_Notifications': { id:'latest-notifications', cat:'Latest Jobs',     qual:'',                   icon:'fa-bell',              label:'Latest Notifications' },
    'Last_Date_Reminder':   { id:'jobs-with-last-date',  cat:'Expiring Soon',   qual:'',                   icon:'fa-clock',             label:'Jobs by Last Date' },
  };

  /* ══════════════════════════════════════════════════════════
   * JSON PROCESSOR — Converts each JSON file → allData items
   * ══════════════════════════════════════════════════════════ */
  function processJsonFile(data, fileName) {
    var extra = [];
    var now   = new Date().toISOString();
    // BUGFIX: the loader fetches '/data/Complete_Jobs_Full_Data.json' (with a path
    // prefix), but the branches below match on the bare filename. Strip any path so
    // the Complete_Jobs parser actually runs and jobs get indexed.
    fileName = String(fileName || '').split('?')[0].split('/').pop();

    /* ── merged_sarkari_data.json ── */
    if (false && fileName === 'merged_sarkari_data_REMOVED') {
      var jobs = Array.isArray(data.jobs) ? data.jobs : [];
      jobs.forEach(function(j) {
        var title = getJobTitle(j);
        if (!title || title.length < 4) return;

        var org   = getJobOrg(j);
        var url   = buildJobUrl(title, j.apply_mode, j.category) || j.apply_online_link || j.official_website_link || '#';
        var dates = j.important_dates || {};
        var lastDate = dates.last_date_to_apply || dates.last_date || '';
        var postDate = j.listing_date || '';

        // Section source display label
        var catLabel = {
          'LATEST_JOBS NEW': 'Latest Jobs New',
          'SR_Latest_Jobs':  'Latest Jobs',
          'STATE_JOBS':      'State Jobs',
          'CENTRAL_JOBS':    'Central Jobs',
          'ADMISSIONS':      'Admissions',
          'UPCOMING_JOBS':   'Upcoming Jobs',
          'OFFLINE_FORM':    'Offline Form',
          'SR_Admit_Card':   'Admit Card',
          'SR_Result':       'Result',
          'SR_Admission':    'Admission',
          'SR_Answer_Key':   'Answer Key',
        }[j.category] || j.category || 'Latest Jobs';

        var lu = now;
        if (postDate) {
          var p = postDate.split('-');
          if (p.length === 3 && p[0].length === 4) lu = postDate + 'T00:00:00';
        }

        extra.push({
          title:         title,
          slug:          url,
          dept:          org,
          postName:      j.post_name || '',
          qual:          '',
          state:         j.job_location || 'All India',
          cat:           catLabel,
          tags:          [title, org, j.post_name||'', catLabel, j.job_location||'',
                          j.category||'', 'sarkari job 2026'].join(' '),
          lastDate:      lastDate,
          icon:          'fa-briefcase',
          lastUpdated:   lu,
          sectionSource: catLabel,
          isJobDetail:   true,
        });
      });
    }

    /* ── Education_Jobs.json ── */
    if (false && fileName === 'Education_Jobs_REMOVED') {
      var sections = Array.isArray(data.sections) ? data.sections : [];
      sections.forEach(function(sec) {
        var secTitle = String(sec.title || sec.id || '').trim();
        var secId    = String(sec.id    || sec.title || '').trim();

        (sec.items || []).forEach(function(item) {
          var title = String(item.name || item.examName || '').trim();
          if (!title || title.length < 4) return;

          var detail  = item.detail || {};
          var seoTags = Array.isArray(detail.seo_tags) ? detail.seo_tags : [];
          var href    = '/education-detail.html?section=' + encodeURIComponent(secId) +
                        '&slug=' + encodeURIComponent(slugifyTitle(title));

          var lu = now;
          if (item.postDate) {
            var parts = item.postDate.split('/');
            if (parts.length === 3) lu = parts[2]+'-'+parts[1]+'-'+parts[0]+'T00:00:00';
          }

          extra.push({
            title:         title,
            slug:          href,
            dept:          item.category || secTitle,
            postName:      item.examName || '',
            qual:          '',
            state:         'All India',
            cat:           secTitle,
            seoTags:       seoTags,
            tags:          [title, secTitle, item.category||'', seoTags.join(' '),
                            'education exam result 2026'].join(' '),
            lastDate:      item.date ? item.date.replace(/Post Date:\s*/i,'') : '',
            icon:          'fa-graduation-cap',
            lastUpdated:   lu,
            sectionSource: secTitle,
            isJobDetail:   false,
          });
        });
      });
    }

    /* ── dailyupdates.json ── */
    if (fileName === 'dailyupdates.json') {
      var sects = Array.isArray(data.sections) ? data.sections
                : Array.isArray(data) ? data : [];
      sects.forEach(function(sec) {
        var secId    = String(sec.id    || sec.title || '').trim();
        var secTitle = String(sec.title || sec.id    || '').trim();

        function getSectionIcon(t) {
          var tl = t.toLowerCase();
          if (/result|merit|score/.test(tl)) return 'fa-trophy';
          if (/admit|hall|call/.test(tl))    return 'fa-id-card';
          if (/answer|key|objection/.test(tl)) return 'fa-key';
          if (/scheme|yojna|yojana/.test(tl)) return 'fa-indian-rupee-sign';
          if (/csc|pdf|link/.test(tl))        return 'fa-file-pdf';
          return 'fa-bell';
        }

        (sec.items || []).forEach(function(item) {
          var title = String(item.name || item.title || '').trim();
          if (!title || title.length < 4) return;
          var href = item.slug ? ('/jobs/' + item.slug + '/') : (item.url || item.link || '#');
          if (!href || href === '#') return;

          extra.push({
            title:         title,
            slug:          href,
            dept:          secTitle,
            postName:      '',
            qual:          '',
            state:         'All India',
            cat:           secTitle,
            tags:          [title, secTitle, 'sarkari update 2026'].join(' '),
            lastDate:      '',
            icon:          getSectionIcon(secTitle),
            lastUpdated:   now,
            sectionSource: secTitle,
            isJobDetail:   false,
          });
        });
      });
    }

    /* ── Complete_Jobs_Full_Data.json ── */
    if (fileName === 'Complete_Jobs_Full_Data.json') {
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        // NEW structure: data.freejobalert_categories[cat] = [job, ...]
        var cats = data.freejobalert_categories || {};
        Object.keys(cats).forEach(function(catKey) {
          var meta = COMPLETE_JOBS_META[catKey] || {
            id: catKey.toLowerCase().replace(/_/g, '-'),
            cat: catKey.replace(/_/g, ' '),
            qual: '',
            icon: 'fa-briefcase',
            label: catKey.replace(/_/g, ' '),
          };

          (Array.isArray(cats[catKey]) ? cats[catKey] : []).forEach(function(job) {
            var bd = job.basic_details || {};
            var title = (bd.job_title || '').trim();
            if (!title) return;
            var org = (bd.organization_name || '').trim();
            var href = resolveJobUrl(job._canonical_slug || job.canonical_slug || '', title);
            if (!href) return;   // no real page on disk → skip (never emit a 404)
            var dates = job.important_dates || {};
            var lastDate = String(
              dates.last_date_to_apply || dates.last_date || dates['Last Date to Apply'] || ''
            ).trim();

            extra.push({
              title:         title,
              slug:          href,
              dept:          org,
              postName:      bd.post_name || '',
              qual:          meta.qual || '',
              state:         'All India',
              cat:           meta.cat,
              tags:          [title, org, meta.id, meta.qual||'',
                              String(bd.short_information||'').slice(0,80),
                              'sarkari job 2026'].join(' '),
              lastDate:      lastDate,
              icon:          meta.icon,
              lastUpdated:   bd.last_updated || now,
              sectionSource: meta.label,
              isJobDetail:   true,
            });
          });
        });

        // Also index sarkari_data jobs
        var sarkariJobs = (data.sarkari_data && data.sarkari_data.jobs) || [];
        sarkariJobs.forEach(function(job) {
          var title = (job.title || '').trim();
          if (!title) return;
          var href = resolveJobUrl(job._canonical_slug || job.canonical_slug || '', title);
          if (!href) return;   // no real page on disk → skip (never emit a 404)
          var dates = job.important_dates || {};
          var lastDate = String(dates['Last Date'] || dates.last_date || '').trim();
          extra.push({
            title:         title,
            slug:          href,
            dept:          job.organization || '',
            postName:      job.post_name || '',
            qual:          '',
            state:         job.job_location || 'All India',
            cat:           job.category || 'Latest Jobs',
            tags:          [title, job.organization||'', job.category||'', 'sarkari job 2026'].join(' '),
            lastDate:      lastDate,
            icon:          'fa-briefcase',
            lastUpdated:   job.listing_date || now,
            sectionSource: 'Latest Jobs',
            isJobDetail:   true,
          });
        });

        // Also index education_jobs and state_jobs (sections[].items[])
        ['education_jobs', 'state_jobs'].forEach(function(blockKey) {
          var block = data[blockKey];
          var secs  = block && Array.isArray(block.sections) ? block.sections : [];
          var srcLabel = blockKey === 'education_jobs' ? 'Education' : 'State Jobs';
          secs.forEach(function(sec) {
            var secCat   = sec.category || sec.title || srcLabel;
            var secState = sec.state || sec.title || 'All India';
            (Array.isArray(sec.items) ? sec.items : []).forEach(function(item) {
              var title = (item.name || item.title || '').trim();
              if (!title) return;
              var href = resolveJobUrl(item._canonical_slug || item.canonical_slug || '', title);
              if (!href) return;   // no real page on disk → skip (never emit a 404)
              extra.push({
                title:         title,
                slug:          href,
                dept:          item.examName || secCat || '',
                postName:      '',
                qual:          '',
                state:         secState,
                cat:           secCat,
                tags:          [title, item.examName||'', secCat, secState, 'sarkari job 2026'].join(' '),
                lastDate:      String(item.postDate || item.date || '').trim(),
                icon:          blockKey === 'education_jobs' ? 'fa-graduation-cap' : 'fa-location-dot',
                lastUpdated:   item.postDate || now,
                sectionSource: srcLabel,
                isJobDetail:   true,
              });
            });
          });
        });
      }
      return extra;
    }

    /* ── state-jobs-data.json ── */
    if (false && fileName === 'state-jobs-data_REMOVED') {
      var sections2 = Array.isArray(data.sections) ? data.sections
                    : Array.isArray(data) ? data : [];
      sections2.forEach(function(sec) {
        var secId    = String(sec.id    || sec.title || '').trim();
        var secTitle = String(sec.title || sec.id    || 'State Jobs').trim();
        var secState = String(sec.state || '').trim();

        (sec.items || []).forEach(function(item) {
          var title = String(item.name || item.title || '').trim();
          if (!title) return;

          var detail    = item.detail || {};
          var bd        = detail.basic_details || {};
          var applyMode = (bd.application_mode || '').toLowerCase();
          var href      = item.url || item.link || '';
          var slug      = slugifyTitle(bd.job_title || title);
          if (slug && slug !== 'official-link') {
            var prefix = applyMode.indexOf('offline') >= 0 ? 'offline-' : '';
            href = '/jobs/' + prefix + slug + '/';
          }
          if (!href) return;

          var seoTags  = Array.isArray(detail.seo_tags) ? detail.seo_tags : [];
          var board    = String(item.board || bd.organization_name || '').trim();
          var dates2   = detail.important_dates || {};
          var lastDate = String(item.lastDate || item.date ||
            dates2.last_date_to_apply || dates2.last_date || '')
            .replace(/^Last Date:\s*/i, '').trim();

          var lu = now;
          if (item.postDate) {
            var p = item.postDate.split('/');
            if (p.length === 3) lu = p[2]+'-'+p[1]+'-'+p[0]+'T00:00:00';
          }

          extra.push({
            title:         title,
            slug:          href,
            dept:          board || secTitle,
            postName:      bd.post_name || item.post_name || '',
            qual:          item.qualification || bd.qualification || '',
            state:         secState || 'All India',
            cat:           'State Jobs',
            seoTags:       seoTags,
            tags:          [title, board, secTitle, secState,
                            seoTags.join(' '),
                            String(bd.short_information||'').slice(0,80),
                            'state jobs sarkari naukri 2026'].join(' '),
            lastDate:      lastDate,
            icon:          'fa-location-dot',
            lastUpdated:   lu,
            sectionSource: secTitle,
            isJobDetail:   true,
          });
        });
      });
    }

    return extra;
  }

  /* ══════════════════════════════════════════════════════════
   * MAIN SEARCH FUNCTION
   * ══════════════════════════════════════════════════════════ */
  function doSearch(query) {
    var q = (query || '').trim().toLowerCase();
    if (!q) return [];

    var qType = detectQueryType(q);
    var queryWords = q.split(/\s+/).filter(function(w){ return w.length >= 1; });
    var meaningfulWords = queryWords.filter(function(w){ return w.length >= 2 && !STOP[w]; });
    var MIN_SCORE = 5;

    var results = allData
      .map(function(item) {
        var s = scoreItem(item, q, queryWords, meaningfulWords, qType);
        if (s >= MIN_SCORE) {
          var c = Object.assign({}, item);
          c._score = s;
          c._qType = qType;
          return c;
        }
        return null;
      })
      .filter(Boolean);

    /* Sort: score desc, then recency desc */
    results.sort(function(a, b) {
      if (b._score !== a._score) return b._score - a._score;
      var ta = a.lastUpdated ? new Date(a.lastUpdated).getTime() : 0;
      var tb = b.lastUpdated ? new Date(b.lastUpdated).getTime() : 0;
      return tb - ta;
    });

    /* Dedup by URL */
    var seen = {};
    results = results.filter(function(r) {
      var k = dedupeKey(r.slug);
      if (seen[k]) return false;
      seen[k] = true;
      return true;
    });

    return results;
  }

  /* ══════════════════════════════════════════════════════════
   * FETCH + INDEX ONE FILE
   * ══════════════════════════════════════════════════════════ */
  function fetchAndIndex(fileName, forceRefresh) {
    return fetch(fileName, { cache: 'default' })
      .then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data) {
        var hash = quickHash(data);
        if (!forceRefresh && lastJsonHashes[fileName] === hash) return 0;
        lastJsonHashes[fileName] = hash;
        var extra = processJsonFile(data, fileName);
        if (forceRefresh) {
          var newSlugs = {};
          extra.forEach(function(i){ newSlugs[dedupeKey(i.slug)] = true; });
          allData = allData.filter(function(d){ return !newSlugs[dedupeKey(d.slug)]; });
        }
        mergeItems(extra);
        
        return extra.length;
      })
      .catch(function(err) {
        
        return 0;
      });
  }

  /* ══════════════════════════════════════════════════════════
   * LOADER — Phase 1 fast, Phase 2 heavy
   * ══════════════════════════════════════════════════════════ */
  function loadJsonFiles() {
    /* Phase 1: fast files */
    var fastFiles = ['dailyupdates.json'];  // Only lightweight file in phase 1

    /* Always add category pages first — zero cost */
    mergeItems(CAT_PAGES.map(function(p) {
      return Object.assign({ lastUpdated: new Date().toISOString() }, p);
    }));

    Promise.all(fastFiles.map(fetchAndIndex))
      .then(function() {
        searchReady = true;
        refreshOpenDropdown();

        /* Phase 2/3: Complete_Jobs_Full_Data is the main source — load on user interaction */
        var heavyLoaded = false;
        function loadHeavy() {
          if (heavyLoaded) return;
          heavyLoaded = true;
          // Wait for the disk-truth slug index so every job URL resolves to a
          // page that actually exists (no 404s), then index the main data file.
          jobIndexPromise.then(function() {
            fetchAndIndex('/data/Complete_Jobs_Full_Data.json').then(function() {
              refreshOpenDropdown();
            });
          });
        }

        /* Trigger heavy load on first real typing */
        document.addEventListener('input', function onType(e) {
          if (e.target && (e.target.id === 'heroSearch' || e.target.id === 'headerSearch')) {
            if ((e.target.value || '').length >= 2) {
              document.removeEventListener('input', onType);
              setTimeout(loadHeavy, 200);
            }
          }
        }, { passive: true });

        /* Also load on idle after 20s */
        if ('requestIdleCallback' in window) {
          requestIdleCallback(loadHeavy, { timeout: 25000 });
        } else {
          setTimeout(loadHeavy, 20000);
        }
      })
      .catch(function(err) {
        searchReady = true;
        console.error('[search-v4] Phase 1 error:', err);
      });
  }

  /* ══════════════════════════════════════════════════════════
   * AUTO REFRESH
   * ══════════════════════════════════════════════════════════ */
  function startAutoRefresh() {
    var lastRefresh = Date.now();
    function doRefresh() {
      if (document.hidden) return;
      if (Date.now() - lastRefresh < CFG.refreshIntervalMs) return;
      lastRefresh = Date.now();
      ['dailyupdates.json'].forEach(function(f) {
        fetchAndIndex(f, true).then(function(n) {
          if (n > 0) refreshOpenDropdown();
        });
      });
    }
    document.addEventListener('visibilitychange', doRefresh, { passive: true });
    setInterval(doRefresh, CFG.refreshIntervalMs);
  }

  function refreshOpenDropdown() {
    var inp  = document.getElementById('heroSearch');
    var drop = document.getElementById('tsjDrop');
    if (inp && inp.value.trim().length >= 1 && drop && drop.classList.contains('open')) {
      inp.dispatchEvent(new Event('input'));
    }
  }

  /* ══════════════════════════════════════════════════════════
   * INJECT CSS
   * ══════════════════════════════════════════════════════════ */
  function injectStyles() {
    if (document.getElementById('tsj-search-styles')) return;
    var style = document.createElement('style');
    style.id = 'tsj-search-styles';
    style.textContent = [
      /* Dropdown container */
      '#tsjDrop{background:#fff;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 16px 48px rgba(13,34,87,.18);z-index:99999;max-height:440px;overflow-y:auto;display:none;animation:tsjFadeIn .14s ease;scrollbar-width:thin;scrollbar-color:#cbd5e1 transparent}',
      '#tsjDrop.open{display:block}',
      '#tsjDrop::-webkit-scrollbar{width:4px}#tsjDrop::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:4px}',
      '@keyframes tsjFadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}',
      /* Result item */
      '.tsj-suggest-item{display:flex;align-items:center;gap:10px;padding:9px 13px;text-decoration:none;color:#0f172a;border-bottom:1px solid #f8fafc;transition:background .1s;cursor:pointer;position:relative}',
      '.tsj-suggest-item:last-child{border-bottom:none}',
      '.tsj-suggest-item:hover,.tsj-suggest-item.tsj-active{background:#eff6ff}',
      /* Priority badge strip — left color bar */
      '.tsj-suggest-item.tsj-p1::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:#16a34a;border-radius:2px 0 0 2px}',
      '.tsj-suggest-item.tsj-p2::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:#1d4ed8;border-radius:2px 0 0 2px}',
      '.tsj-suggest-item.tsj-p3::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:#7c3aed;border-radius:2px 0 0 2px}',
      /* Icon */
      '.tsj-si-icon{width:32px;height:32px;border-radius:8px;background:#eff6ff;color:#1a56db;display:flex;align-items:center;justify-content:center;font-size:.8rem;flex-shrink:0}',
      '.tsj-si-icon.ico-green{background:#dcfce7;color:#16a34a}',
      '.tsj-si-icon.ico-orange{background:#fff7ed;color:#ea580c}',
      '.tsj-si-icon.ico-purple{background:#f5f3ff;color:#7c3aed}',
      '.tsj-si-icon.ico-red{background:#fff1f2;color:#be123c}',
      '.tsj-si-icon.ico-teal{background:#f0fdfa;color:#0d9488}',
      /* Body */
      '.tsj-si-body{flex:1;min-width:0;overflow:hidden}',
      '.tsj-si-title{display:block;font-size:.83rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#0f172a}',
      '.tsj-si-meta{display:flex;align-items:center;gap:5px;margin-top:2px;flex-wrap:wrap}',
      '.tsj-badge-pill{display:inline-block;font-size:.6rem;font-weight:700;padding:1px 6px;border-radius:10px;white-space:nowrap}',
      '.tsj-b-job{background:#eff6ff;color:#1d4ed8}',
      '.tsj-b-result{background:#f0fdf4;color:#16a34a}',
      '.tsj-b-admit{background:#fef3c7;color:#b45309}',
      '.tsj-b-edu{background:#f5f3ff;color:#7c3aed}',
      '.tsj-b-state{background:#fff7ed;color:#c2410c}',
      '.tsj-b-cat{background:#f1f5f9;color:#475569}',
      '.tsj-b-date{background:#fff1f2;color:#be123c;font-size:.58rem}',
      '.tsj-si-arr{color:#cbd5e1;font-size:.72rem;flex-shrink:0}',
      '.tsj-suggest-item:hover .tsj-si-arr,.tsj-suggest-item.tsj-active .tsj-si-arr{color:#1a56db}',
      /* Highlight */
      'mark.srch-hl{background:#fef08a;color:#92400e;border-radius:2px;padding:0 1px;font-style:normal}',
      /* Section headers inside dropdown */
      '.tsj-drop-section-hd{padding:5px 13px 3px;font-size:.62rem;font-weight:800;color:#94a3b8;letter-spacing:.06em;text-transform:uppercase;border-bottom:1px solid #f1f5f9;background:#fafbfc}',
      /* Recent / Trending */
      '.tsj-recent{padding:10px 13px 8px}',
      '.tsj-recent-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:7px;font-size:.7rem;font-weight:800;color:#475569}',
      '.tsj-clear-btn{background:none;border:1px solid #e2e8f0;border-radius:6px;padding:2px 8px;font-size:.66rem;color:#94a3b8;cursor:pointer;font-family:inherit}',
      '.tsj-clear-btn:hover{color:#ef4444;border-color:#ef4444}',
      '.tsj-chip-wrap{display:flex;flex-wrap:wrap;gap:5px}',
      '.tsj-chip{background:#f8fafc;color:#475569;border:1px solid #e2e8f0;border-radius:20px;padding:4px 10px;font-size:.7rem;font-weight:600;cursor:pointer;font-family:inherit;transition:all .12s;white-space:nowrap}',
      '.tsj-chip:hover{background:#eff6ff;color:#1a56db;border-color:#bfdbfe}',
      /* Loading / empty */
      '.tsj-loading-msg,.tsj-no-suggest{padding:14px;font-size:.8rem;color:#64748b;text-align:center}',
      /* Footer */
      '.tsj-drop-footer{display:flex;align-items:center;justify-content:center;gap:6px;padding:8px 13px;font-size:.72rem;font-weight:700;color:#64748b;border-top:1px solid #f1f5f9;background:#fafbfc;border-radius:0 0 14px 14px}',
      /* Query type indicator */
      '.tsj-qtype-tag{display:inline-flex;align-items:center;gap:3px;font-size:.6rem;font-weight:700;padding:1px 7px;border-radius:10px;background:#f0fdf4;color:#16a34a}',
      '.tsj-qtype-tag.specific{background:#eff6ff;color:#1d4ed8}',
      '@media(max-width:480px){#tsjDrop{border-radius:10px;max-height:380px}.tsj-si-title{font-size:.79rem}}',
    ].join('');
    document.head.appendChild(style);
  }

  /* ══════════════════════════════════════════════════════════
   * RENDER HELPERS
   * ══════════════════════════════════════════════════════════ */
  function getIconClass(item) {
    var cat = ((item.cat || '') + ' ' + (item.sectionSource || '')).toLowerCase();
    if (/result|merit|score/.test(cat))  return 'ico-green';
    if (/admit|hall|call/.test(cat))     return 'ico-orange';
    if (/education|exam|gate|neet|board/.test(cat)) return 'ico-purple';
    if (/state|haryana|delhi|punjab/.test(cat))     return 'ico-teal';
    if (/police|army|defence|crpf|bsf/.test(cat))  return 'ico-red';
    return '';
  }

  function getBadgeClass(item) {
    var c = ((item.cat||'')+(item.sectionSource||'')).toLowerCase();
    if (/result/.test(c))  return 'tsj-b-result';
    if (/admit/.test(c))   return 'tsj-b-admit';
    if (/education|exam/.test(c)) return 'tsj-b-edu';
    if (/state/.test(c))   return 'tsj-b-state';
    if (/category|section|filter/.test(c)) return 'tsj-b-cat';
    return 'tsj-b-job';
  }

  function getPriorityClass(score) {
    if (score >= 600) return ' tsj-p1';
    if (score >= 200) return ' tsj-p2';
    if (score >= 80)  return ' tsj-p3';
    return '';
  }

  function renderItem(item, q, idx) {
    var pClass  = getPriorityClass(item._score || 0);
    var icClass = getIconClass(item);
    var bdClass = getBadgeClass(item);
    var sec     = esc(item.sectionSource || item.cat || '');
    var state   = (item.state && item.state !== 'All India') ? ' · ' + esc(item.state) : '';
    var dateHtml = item.lastDate
      ? '<span class="tsj-badge-pill tsj-b-date"><i class="fa-solid fa-clock" style="font-size:.55rem"></i> ' + esc(item.lastDate) + '</span>'
      : '';

    return '<a class="tsj-suggest-item' + pClass + '" href="' + esc(item.slug) + '" data-idx="' + idx + '" role="option">' +
      '<span class="tsj-si-icon ' + icClass + '"><i class="fa-solid ' + esc(item.icon || 'fa-briefcase') + '"></i></span>' +
      '<span class="tsj-si-body">' +
        '<span class="tsj-si-title">' + highlight(item.title, q) + '</span>' +
        '<span class="tsj-si-meta">' +
          (sec ? '<span class="tsj-badge-pill ' + bdClass + '">' + sec + state + '</span>' : '') +
          dateHtml +
        '</span>' +
      '</span>' +
      '<span class="tsj-si-arr"><i class="fa-solid fa-arrow-right"></i></span>' +
      '</a>';
  }

  /* ══════════════════════════════════════════════════════════
   * HERO SEARCH SETUP
   * ══════════════════════════════════════════════════════════ */
  function setupHeroSearch() {
    var input = document.getElementById('heroSearch');
    var btn   = document.getElementById('heroSearchBtn');
    if (!input) return;

    injectStyles();

    /* Remove old dropdown if any */
    ['searchSuggest','heroSearchResults'].forEach(function(id) {
      var el = document.getElementById(id); if (el) el.remove();
    });

    /* Create dropdown */
    var drop = document.getElementById('tsjDrop');
    if (!drop) {
      drop = document.createElement('div');
      drop.id = 'tsjDrop';
      drop.setAttribute('role', 'listbox');
      document.body.appendChild(drop);
    }

    /* Position dropdown below search box */
    function positionDrop() {
      var box  = input.closest('.hero-search-box') || input;
      var rect = box.getBoundingClientRect();
      drop.style.cssText = 'position:fixed;top:'+(rect.bottom+5)+'px;left:'+rect.left+'px;width:'+rect.width+'px;max-height:440px;z-index:99999';
    }
    requestAnimationFrame(function(){ requestAnimationFrame(positionDrop); });
    window.addEventListener('resize', positionDrop, { passive: true });
    window.addEventListener('scroll', function(){ if(drop.classList.contains('open')) positionDrop(); }, true);

    function openDrop(html) {
      positionDrop();
      drop.innerHTML = html;
      drop.classList.add('open');
      /* Bind chip clicks */
      drop.querySelectorAll('.tsj-chip').forEach(function(b) {
        b.addEventListener('click', function() {
          input.value = b.dataset.q;
          runSuggest(b.dataset.q);
        });
      });
      var clearBtn = drop.querySelector('#tsjClearRecent');
      if (clearBtn) {
        clearBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          try { localStorage.removeItem(CFG.recentKey); } catch(e2) {}
          showDefaultDrop();
        });
      }
    }

    function closeDrop() {
      drop.classList.remove('open');
      drop.innerHTML = '';
      activeIndex = -1;
      suggestItems = [];
    }

    /* TRENDING chips */
    var TRENDING = [
      {label:'SSC GD',        q:'SSC GD'},
      {label:'Railway Jobs',  q:'railway'},
      {label:'10th Pass',     q:'10th pass'},
      {label:'Police',        q:'police constable'},
      {label:'Admit Card',    q:'admit card'},
      {label:'Result',        q:'result'},
      {label:'Bank Jobs',     q:'bank'},
      {label:'UPSC',          q:'upsc'},
      {label:'Haryana Jobs',  q:'haryana'},
      {label:'Army',          q:'army'},
    ];

    function showDefaultDrop() {
      var recent = getRecent();
      var html = '';
      if (recent.length) {
        html += '<div class="tsj-recent">' +
          '<div class="tsj-recent-hd"><span><i class="fa-solid fa-clock-rotate-left"></i> Recent Searches</span>' +
          '<button type="button" id="tsjClearRecent" class="tsj-clear-btn">Clear</button></div>' +
          '<div class="tsj-chip-wrap">' +
          recent.map(function(r){ return '<button class="tsj-chip" type="button" data-q="'+esc(r)+'">'+esc(r)+'</button>'; }).join('') +
          '</div></div>';
      }
      html += '<div class="tsj-recent" style="border-top:'+(recent.length?'1px solid #f1f5f9':'none')+'">' +
        '<div class="tsj-recent-hd"><span><i class="fa-solid fa-fire" style="color:#ea580c"></i> Trending Searches</span></div>' +
        '<div class="tsj-chip-wrap">' +
        TRENDING.map(function(t){ return '<button class="tsj-chip" type="button" data-q="'+esc(t.q)+'">'+esc(t.label)+'</button>'; }).join('') +
        '</div></div>';
      openDrop(html);
    }

    /* MAIN SUGGEST RUNNER */
    function runSuggest(q) {
      q = (q || '').trim();
      if (!q) { showDefaultDrop(); return; }

      if (!searchReady) {
        openDrop('<div class="tsj-loading-msg"><i class="fa-solid fa-spinner fa-spin"></i> Job data load ho raha hai…</div>');
        return;
      }

      var qType   = detectQueryType(q);
      var allRes  = doSearch(q);
      var shown   = allRes.slice(0, CFG.maxSuggest);
      suggestItems = shown;
      activeIndex  = -1;

      if (!shown.length) {
        openDrop('<div class="tsj-no-suggest">No results for "<strong>' + esc(q) + '</strong>"<br><small>Try: SSC · Railway · Police · Bank · Result · Haryana</small></div>');
        return;
      }

      /* Separate job detail pages vs category pages for SPECIFIC queries */
      var jobItems  = shown.filter(function(r){ return r.isJobDetail; });
      var catItems  = shown.filter(function(r){ return !r.isJobDetail; });

      var html = '';

      /* Query type indicator */
      html += '<div style="padding:5px 13px 4px;background:#fafbfc;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;gap:6px">' +
        '<span style="font-size:.67rem;font-weight:700;color:#94a3b8">Search:</span>' +
        '<span class="tsj-qtype-tag '+(qType==='SPECIFIC'?'specific':'')+'">' +
        '<i class="fa-solid '+(qType==='SPECIFIC'?'fa-bullseye':'fa-filter')+'"></i> ' +
        (qType==='SPECIFIC' ? 'Job Search' : 'Category Search') +
        '</span></div>';

      if (qType === 'SPECIFIC') {
        /* SPECIFIC: Job pages first, then category pages */
        if (jobItems.length) {
          html += '<div class="tsj-drop-section-hd"><i class="fa-solid fa-briefcase"></i> Job Detail Pages</div>';
          html += jobItems.slice(0, 8).map(function(r, i){ return renderItem(r, q, i); }).join('');
        }
        if (catItems.length) {
          html += '<div class="tsj-drop-section-hd"><i class="fa-solid fa-filter"></i> Category Pages</div>';
          html += catItems.slice(0, 3).map(function(r, i){ return renderItem(r, q, jobItems.length + i); }).join('');
        }
      } else {
        /* GENERAL: Category pages first, then jobs */
        if (catItems.length) {
          html += '<div class="tsj-drop-section-hd"><i class="fa-solid fa-filter"></i> Category & Section Pages</div>';
          html += catItems.slice(0, 5).map(function(r, i){ return renderItem(r, q, i); }).join('');
        }
        if (jobItems.length) {
          html += '<div class="tsj-drop-section-hd"><i class="fa-solid fa-briefcase"></i> Related Jobs</div>';
          html += jobItems.slice(0, 5).map(function(r, i){ return renderItem(r, q, catItems.length + i); }).join('');
        }
      }

      var total = allRes.length;
      if (total > CFG.maxSuggest) {
        html += '<div class="tsj-drop-footer"><i class="fa-solid fa-list"></i> ' + total + ' results found · Refine your search</div>';
      }

      openDrop(html);
    }

    /* Keyboard navigation */
    input.addEventListener('keydown', function(e) {
      var items = drop.querySelectorAll('.tsj-suggest-item');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIndex = Math.min(activeIndex + 1, items.length - 1);
        items.forEach(function(el, i){ el.classList.toggle('tsj-active', i === activeIndex); });
        if (items[activeIndex]) items[activeIndex].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, -1);
        items.forEach(function(el, i){ el.classList.toggle('tsj-active', i === activeIndex); });
      } else if (e.key === 'Enter') {
        e.preventDefault();
        var active = drop.querySelector('.tsj-suggest-item.tsj-active');
        if (active) {
          saveRecent(input.value.trim()); window.location.href = active.href; closeDrop();
        } else if (input.value.trim()) {
          saveRecent(input.value.trim()); runSuggest(input.value.trim());
        }
      } else if (e.key === 'Escape') {
        closeDrop();
      }
    });

    var dSuggest = debounce(function(q){ runSuggest(q); }, CFG.debounceMs);
    input.addEventListener('input', function(){ dSuggest(this.value); });
    input.addEventListener('focus', function() {
      if (this.value.trim().length >= 1) runSuggest(this.value);
      else showDefaultDrop();
    });

    if (btn) {
      btn.addEventListener('click', function() {
        var q = input.value.trim();
        if (q) { saveRecent(q); runSuggest(q); input.focus(); }
      });
    }

    drop.addEventListener('click', function(e) {
      var item = e.target.closest('.tsj-suggest-item');
      if (item) { saveRecent(input.value.trim()); closeDrop(); }
    });

    document.addEventListener('click', function(e) {
      var box = input.closest('.hero-search-box') || input.parentElement;
      if (!drop.contains(e.target) && !box.contains(e.target)) closeDrop();
    });

    var mobileBtn = document.getElementById('mobileSearchBtn');
    if (mobileBtn) {
      mobileBtn.addEventListener('click', function() {
        var hero = document.getElementById('hero-search-section');
        if (hero) { hero.scrollIntoView({ behavior:'smooth', block:'start' }); setTimeout(function(){ input.focus(); }, 400); }
      });
    }
  }

  /* ══════════════════════════════════════════════════════════
   * HEADER SEARCH
   * ══════════════════════════════════════════════════════════ */
  function setupHeaderSearch() {
    var hInput = document.getElementById('headerSearch');
    var hBtn   = document.getElementById('headerSearchBtn');

    function goToHero(q) {
      var heroInput = document.getElementById('heroSearch');
      var hero = document.getElementById('hero-search-section');
      if (heroInput) {
        if (hero) hero.scrollIntoView({ behavior:'smooth', block:'start' });
        setTimeout(function() {
          heroInput.value = q;
          heroInput.dispatchEvent(new Event('input'));
          heroInput.focus();
        }, 350);
      }
    }

    if (hInput && hBtn) {
      hBtn.addEventListener('click', function(){ if(hInput.value.trim()) goToHero(hInput.value.trim()); });
      hInput.addEventListener('keydown', function(e){
        if (e.key === 'Enter' && hInput.value.trim()) goToHero(hInput.value.trim());
      });
    }

    var openBtn = document.getElementById('openSearchBtn');
    if (openBtn) {
      openBtn.addEventListener('click', function() {
        var heroInput = document.getElementById('heroSearch');
        if (heroInput) {
          var hero = document.getElementById('hero-search-section');
          if (hero) hero.scrollIntoView({ behavior:'smooth', block:'start' });
          setTimeout(function(){ heroInput.focus(); }, 350);
        }
      });
    }
  }

  /* ══════════════════════════════════════════════════════════
   * MENU SEARCH SETUP
   * ══════════════════════════════════════════════════════════ */
  function setupMenuSearch() {
    var menuInput = document.getElementById('menuSearchInput');
    if (!menuInput) return;
    menuInput.addEventListener('keydown', function(e){
      if (e.key === 'Enter' && this.value.trim()) {
        var q = this.value.trim();
        saveRecent(q);
        var heroInput = document.getElementById('heroSearch');
        var hero = document.getElementById('hero-search-section');
        if (heroInput && hero) {
          document.getElementById('mobileMenu') && (document.getElementById('mobileMenu').hidden = true);
          document.getElementById('menuOverlay') && (document.getElementById('menuOverlay').hidden = true);
          document.body.style.overflow = '';
          hero.scrollIntoView({ behavior:'smooth', block:'start' });
          setTimeout(function(){
            heroInput.value = q;
            heroInput.dispatchEvent(new Event('input'));
            heroInput.focus();
          }, 400);
        }
      }
    });
  }

  /* ══════════════════════════════════════════════════════════
   * SEARCH PAGE HANDLER
   * ══════════════════════════════════════════════════════════ */
  function setupSearchPage() {
    var container = document.getElementById('searchPageResults');
    if (!container) return;

    var params = new URLSearchParams(location.search);
    var q = params.get('q') || '';

    if (q) {
      document.title = q + ' – Jobs Search | Top Sarkari Jobs 2026';
      var meta = document.querySelector('meta[name="description"]');
      if (meta) meta.content = 'Search results for "' + q + '" – Find government jobs, results, admit cards.';
    }

    var pageInput = document.getElementById('searchPageInput');
    if (pageInput && q) pageInput.value = q;

    function renderPage(query) {
      var results = doSearch(query);
      if (!results.length) {
        container.innerHTML = '<p style="color:#64748b">No results for "<strong>' + esc(query) + '</strong>". Try: SSC, Railway, Bank, Police…</p>';
        return;
      }
      container.innerHTML = '<p style="font-size:.88rem;color:#475569;font-weight:700;margin-bottom:12px">' +
        results.length + ' results for "<strong>' + esc(query) + '</strong>"</p>' +
        '<div style="display:flex;flex-direction:column;gap:8px">' +
        results.slice(0, 60).map(function(r) {
          return '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px">' +
            '<a href="' + esc(r.slug) + '" style="font-size:.86rem;font-weight:800;color:#1a56db;text-decoration:none;display:block;margin-bottom:4px">' +
            highlight(r.title, query) + '</a>' +
            '<div style="font-size:.72rem;color:#64748b">' + esc(r.sectionSource || r.cat || '') +
            (r.state && r.state !== 'All India' ? ' · ' + esc(r.state) : '') + '</div>' +
            (r.lastDate ? '<div style="font-size:.7rem;color:#be123c;margin-top:4px"><i class="fa-solid fa-clock"></i> ' + esc(r.lastDate) + '</div>' : '') +
            '</div>';
        }).join('') + '</div>';
    }

    if (q) {
      saveRecent(q);
      if (searchReady) {
        renderPage(q);
      } else {
        container.innerHTML = '<p style="color:#64748b"><i class="fa-solid fa-spinner fa-spin"></i> Loading search data…</p>';
        var checkReady = setInterval(function() {
          if (searchReady) { clearInterval(checkReady); renderPage(q); }
        }, 200);
        setTimeout(function(){ clearInterval(checkReady); renderPage(q); }, 10000);
      }
    }
  }

  /* ══════════════════════════════════════════════════════════
   * EXTERNAL API — window.tsjSearch
   * ══════════════════════════════════════════════════════════ */
  window.tsjSearch = {
    search: doSearch,
    go: function(q) {
      var heroInput = document.getElementById('heroSearch');
      var hero = document.getElementById('hero-search-section');
      if (!heroInput) return;
      if (hero) hero.scrollIntoView({ behavior:'smooth', block:'start' });
      setTimeout(function() {
        heroInput.value = q;
        heroInput.dispatchEvent(new Event('input'));
        heroInput.focus();
      }, 350);
    },
    getData: function(){ return allData; },
    getCount: function(){ return allData.length; },
    isReady: function(){ return searchReady; },
  };

  /* ── Legacy alias ── */
  window.__SEO_updateSection = function(){};

  /* tsjSearchIndex: array-compatible shim so script.js can .push() items into search index */
  var _tsjLegacyQueue = Array.isArray(window.tsjSearchIndex) ? window.tsjSearchIndex : [];
  window.tsjSearchIndex = {
    push: function(item) {
      if (!item || !item.title) return;
      /* Merge into allData so search finds these items too */
      var key = dedupeKey(item.slug || '');
      if (!key) return;
      var seen = {};
      allData.forEach(function(d){ seen[dedupeKey(d.slug||'')] = true; });
      if (!seen[key]) {
        item.lastUpdated = item.lastUpdated || new Date().toISOString();
        item.isJobDetail = true;
        allData.push(item);
      }
    },
    search: doSearch,
    go: window.tsjSearch.go,
    getData: function(){ return allData; },
    getCount: function(){ return allData.length; },
    isReady: function(){ return searchReady; },
  };
  /* Flush any items queued before smart-search loaded */
  if (_tsjLegacyQueue.length) {
    _tsjLegacyQueue.forEach(function(item){ window.tsjSearchIndex.push(item); });
  }

  /* ══════════════════════════════════════════════════════════
   * INIT
   * ══════════════════════════════════════════════════════════ */
  function init() {
    loadJsonFiles();
    startAutoRefresh();

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        setupHeroSearch();
        setupHeaderSearch();
        setupMenuSearch();
        setupSearchPage();
      });
    } else {
      setupHeroSearch();
      setupHeaderSearch();
      setupMenuSearch();
      setupSearchPage();
    }
  }

  init();

})();
