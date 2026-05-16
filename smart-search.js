/**
 * ============================================================
 * TOP SARKARI JOBS – SMART SEARCH SYSTEM v3.0
 * Features:
 *   ✅ Promise.all() parallel preload — first load se kaam kare
 *   ✅ Cache busting — timestamp + no-store so purana cache na aaye
 *   ✅ dailyupdates.json — ALL sections searchable (non-job bhi)
 *   ✅ Auto-refresh — har 5 min me background reload
 *   ✅ Change detection — naya data milne par index replace ho
 *   ✅ Dedup by URL — duplicate entries remove
 *   ✅ Instant typing results — debounce 150ms
 *   ✅ Direct page navigation on click
 *   ✅ Mobile friendly & lightweight
 * ============================================================
 */
(function () {
  'use strict';

  /* ── CONFIG ─────────────────────────────────────────────── */
  const CFG = {
    fuseJs: 'https://cdnjs.cloudflare.com/ajax/libs/fuse.js/7.0.0/fuse.min.js',
    jsonFiles: [
      'dailyupdates.json',
      'merged_sarkari_data.json',
      'state-jobs-data.json',
      'Complete_Jobs_Full_Data.json',
    ],
    maxSuggest: 18,
    debounceMs: 150,
    recentKey: 'tsj_recent_v3',
    maxRecent: 8,
    refreshIntervalMs: 5 * 60 * 1000,
    cacheBust: () => '?_cb=' + Date.now(),
  };

  /* ── TRENDING TAGS ──────────────────────────────────────── */
  const TRENDING = [
    { label: 'Railway Jobs',   q: 'railway',    icon: 'fa-train' },
    { label: 'Police Jobs',    q: 'police',     icon: 'fa-shield-halved' },
    { label: 'Haryana Jobs',   q: 'haryana',    icon: 'fa-location-dot' },
    { label: '10th Pass Jobs', q: '10th pass',  icon: 'fa-certificate' },
    { label: 'Admit Card',     q: 'admit card', icon: 'fa-id-card' },
    { label: 'SSC CGL',        q: 'ssc cgl',    icon: 'fa-medal' },
    { label: 'Bank Jobs',      q: 'bank',       icon: 'fa-building-columns' },
    { label: 'Army Jobs',      q: 'army',       icon: 'fa-star' },
    { label: 'Results',        q: 'result',     icon: 'fa-trophy' },
    { label: 'ITI Jobs',       q: 'iti',        icon: 'fa-tools' },
  ];

  /* ── STATE ──────────────────────────────────────────────── */
  let allData = [];
  let fuseInstance = null;
  let fuseLoaded = false;
  let activeIndex = -1;
  let suggestItems = [];
  let searchReady = false;
  let lastJsonHashes = {};

  /* ── UTILS ──────────────────────────────────────────────── */
  function esc(s) {
    return String(s || '').replace(/[&<>"]/g, function(c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }

  function debounce(fn, ms) {
    var t; return function() {
      var args = arguments, ctx = this;
      clearTimeout(t); t = setTimeout(function(){ fn.apply(ctx, args); }, ms);
    };
  }

  function highlight(text, query) {
    if (!query || !text) return esc(text);
    var words = query.trim().split(/\s+/).filter(function(w){ return w.length > 1; });
    var result = esc(text);
    words.forEach(function(w) {
      var rx = new RegExp('(' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      result = result.replace(rx, '<mark class="srch-hl">$1</mark>');
    });
    return result;
  }

  function slugifyTitle(raw) {
    return String(raw || '')
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/[\s-]+/g, '-')
      .slice(0, 120)
      .replace(/^-+|-+$/g, '') || 'official-link';
  }

  /* ── RECENT SEARCHES ────────────────────────────────────── */
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

  /* ── FUSE.JS ────────────────────────────────────────────── */
  function loadFuse(cb) {
    if (window.Fuse) { cb(); return; }
    var s = document.createElement('script');
    s.src = CFG.fuseJs;
    s.onload = cb;
    s.onerror = cb;
    document.head.appendChild(s);
  }

  function buildFuse(data) {
    if (!window.Fuse) return;
    fuseInstance = new window.Fuse(data, {
      keys: [
        { name: 'title', weight: 0.45 },
        { name: 'tags',  weight: 0.25 },
        { name: 'dept',  weight: 0.10 },
        { name: 'cat',   weight: 0.08 },
        { name: 'state', weight: 0.07 },
        { name: 'qual',  weight: 0.05 },
      ],
      threshold: 0.5,
      includeScore: true,
      ignoreLocation: true,
      minMatchCharLength: 1,
    });
    fuseLoaded = true;
  }

  /* ── DEDUP KEY ──────────────────────────────────────────── */
  function dedupeKey(slug) {
    if (!slug) return slug;
    try {
      var u = new URL(slug, 'https://x.com');
      return (u.searchParams.get('slug') || u.pathname).toLowerCase().trim();
    } catch(e) {
      return slug.split('?')[0].toLowerCase().trim();
    }
  }

  /* ── URL BUILDERS ───────────────────────────────────────── */
  function buildJobHref(job, secId) {
    var bd = job.basic_details || {};
    var rawTitle = job.title || job.post_name || bd.job_title || bd.post_name || '';
    var slug = job.slug || slugifyTitle(rawTitle);
    if (!slug || slug === 'official-link') return job.source_url || job.url || job.link || '#';
    var applyMode = (job.apply_mode || bd.application_mode || '').toLowerCase();
    var prefix = applyMode === 'offline' ? 'offline-' : '';
    return 'job.html?slug=' + encodeURIComponent(prefix + slug) +
           (secId ? '&section=' + encodeURIComponent(secId) : '');
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

  /* ── MERGE INTO allData ─────────────────────────────────── */
  function mergeItems(extra) {
    if (!extra.length) return false;
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
    if (added > 0) {
      allData.sort(function(a, b) {
        var ta = a.lastUpdated ? new Date(a.lastUpdated).getTime() : 0;
        var tb = b.lastUpdated ? new Date(b.lastUpdated).getTime() : 0;
        return tb - ta;
      });
      return true;
    }
    return false;
  }

  /* ── COMPLETE_JOBS META ─────────────────────────────────── */
  var COMPLETE_JOBS_META = {
    Latest_Notifications: { id:'Latest Notifications',   icon:'fa-bell',             qual:'',               cat:'Latest'      },
    '10TH_Pass':          { id:'10th Pass Jobs',          icon:'fa-graduation-cap',   qual:'10th Pass',      cat:'State Jobs'  },
    '8TH_Pass':           { id:'8th Pass Jobs',           icon:'fa-book',             qual:'8th Pass',       cat:'State Jobs'  },
    '12TH_Pass':          { id:'12th Pass Jobs',          icon:'fa-graduation-cap',   qual:'12th Pass',      cat:'State Jobs'  },
    Diploma:              { id:'Diploma Jobs',            icon:'fa-scroll',           qual:'Diploma',        cat:'Others'      },
    ITI:                  { id:'ITI Jobs',                icon:'fa-tools',            qual:'ITI',            cat:'ITI Jobs'    },
    B_Tech_BE:            { id:'B.Tech Jobs',             icon:'fa-microchip',        qual:'B.Tech',         cat:'Engineering' },
    B_Com:                { id:'B.Com Jobs',              icon:'fa-chart-line',       qual:'B.Com',          cat:'Others'      },
    Any_Graduate:         { id:'Graduation Jobs',         icon:'fa-university',       qual:'Graduation',     cat:'Others'      },
    Any_Post_Graduate:    { id:'Post Graduation Jobs',    icon:'fa-user-tie',         qual:'Post Graduation',cat:'Others'      },
    Railway_Jobs:         { id:'Railway Jobs',            icon:'fa-train',            qual:'',               cat:'Railway'     },
    Police_Defence:       { id:'Police Jobs',             icon:'fa-shield-halved',    qual:'',               cat:'Police'      },
    Teaching_Faculty:     { id:'Teaching Jobs',           icon:'fa-chalkboard-user',  qual:'B.Ed',           cat:'Teaching'    },
    Bank_Jobs:            { id:'Bank Jobs',               icon:'fa-building-columns', qual:'Graduation',     cat:'Bank'        },
    Medical_Hospital:     { id:'Medical Jobs',            icon:'fa-stethoscope',      qual:'',               cat:'Medical'     },
    Last_Date_Reminder:   { id:'Last Date Reminder',      icon:'fa-clock',            qual:'',               cat:'Latest'      },
    SSC_Jobs:             { id:'SSC Jobs',                icon:'fa-medal',            qual:'',               cat:'SSC'         },
    UPSC_Jobs:            { id:'UPSC Jobs',               icon:'fa-graduation-cap',   qual:'Graduation',     cat:'UPSC'        },
    Haryana_Jobs:         { id:'Haryana Jobs',            icon:'fa-location-dot',     qual:'',               cat:'State Jobs'  },
    Defence_Jobs:         { id:'Defence Jobs',            icon:'fa-star',             qual:'',               cat:'Defence'     },
  };

  /* ══════════════════════════════════════════════════════════
   * PROCESS ONE JSON FILE
   *
   * KEY FIX for dailyupdates.json:
   * Ab SABHI sections include hain — Govt Scheme, CSC PDF,
   * CSC Link, Top 20 Jobs, Today Updates, sab kuch searchable hai.
   * name + url dono index me aate hain.
   * ══════════════════════════════════════════════════════════ */
  function processJsonFile(data, fileName) {
    var extra = [];

    /* ── 1. dailyupdates.json ─────────────────────────────── */
    if (fileName === 'dailyupdates.json') {
      var sections = Array.isArray(data.sections) ? data.sections
        : Array.isArray(data) ? data : [];

      function getSectionIcon(secTitle) {
        var t = (secTitle || '').toLowerCase();
        if (t.indexOf('scheme') >= 0 || t.indexOf('yojna') >= 0 || t.indexOf('yojana') >= 0) return 'fa-seedling';
        if (t.indexOf('pdf') >= 0) return 'fa-file-pdf';
        if (t.indexOf('link') >= 0 || t.indexOf('csc') >= 0) return 'fa-link';
        if (t.indexOf('job') >= 0 || t.indexOf('naukri') >= 0) return 'fa-briefcase';
        if (t.indexOf('result') >= 0) return 'fa-trophy';
        if (t.indexOf('admit') >= 0) return 'fa-id-card';
        if (t.indexOf('headline') >= 0 || t.indexOf('top') >= 0) return 'fa-newspaper';
        return 'fa-bell';
      }

      function getCatFromSection(secTitle) {
        var t = (secTitle || '').toLowerCase();
        if (t.indexOf('result') >= 0)               return 'Result';
        if (t.indexOf('admit') >= 0)                return 'Admit Card';
        if (t.indexOf('answer key') >= 0)           return 'Answer Key';
        if (t.indexOf('admission') >= 0)            return 'Admission';
        if (t.indexOf('scheme') >= 0 || t.indexOf('yojna') >= 0) return 'Govt Scheme';
        if (t.indexOf('pdf') >= 0)                  return 'PDF';
        if (t.indexOf('link') >= 0 || t.indexOf('csc') >= 0) return 'Important Link';
        if (t.indexOf('job') >= 0 || t.indexOf('naukri') >= 0) return 'Latest Job';
        return 'Update';
      }

      sections.forEach(function(sec) {
        var secTitle = String(sec.title || sec.id || '').trim();
        var secId    = String(sec.id    || sec.title || '').trim();
        var secIcon  = String(sec.icon || '').replace(/^fa-solid\s+/, '') || getSectionIcon(secTitle);
        var cat      = getCatFromSection(secTitle);

        console.log('[smart-search] dailyupdates section:', secTitle, '— Items:', (sec.items || []).length);

        (sec.items || []).forEach(function(item) {
          var title = String(item.name || item.title || '').trim();
          if (!title || title.length < 5) return;

          var url = item.url || item.link || '';
          if (!url || url === '#') return;

          // Skip pure navigation links
          if (/^view\.html\?section=/i.test(url)) return;

          // Build href
          var href = url;
          if (item.slug) {
            href = 'job.html?slug=' + encodeURIComponent(item.slug)
                 + '&section=' + encodeURIComponent(secId);
          }

          var lastDate = item.date || item.lastDate || item.last_date || '';

          var lastUpdated = new Date().toISOString();
          if (item.updated_at) {
            lastUpdated = item.updated_at;
          } else if (item.postDate) {
            var pd = String(item.postDate).split('/');
            if (pd.length === 3) lastUpdated = pd[2] + '-' + pd[1] + '-' + pd[0] + 'T00:00:00';
          } else if (lastDate && /\d{4}-\d{2}-\d{2}/.test(lastDate)) {
            lastUpdated = lastDate + 'T00:00:00';
          }

          var tags = [
            title, secTitle,
            item.board || '',
            item.organization || '',
            item.qualification || '',
            cat, 'sarkari'
          ].filter(Boolean).join(' ');

          extra.push({
            title: title,
            slug: href,
            dept: String(item.board || item.organization || secTitle).trim(),
            qual: String(item.qualification || '').trim(),
            state: String(item.state || 'All India').trim(),
            cat: cat,
            tags: tags,
            lastDate: lastDate,
            icon: secIcon,
            lastUpdated: lastUpdated,
            sectionSource: secTitle,
          });
        });
      });

      console.log('[smart-search] dailyupdates.json — Total extracted:', extra.length);
    }

    /* ── 2. merged_sarkari_data.json ────────────────────── */
    if (fileName === 'merged_sarkari_data.json') {
      var mainJobs = Array.isArray(data.jobs) ? data.jobs : [];
      mainJobs.forEach(function(j) {
        var title = getJobTitle(j);
        if (!title) return;
        var org   = getJobOrg(j);
        var href  = buildJobHref(j, 'Latest Jobs');
        if (!href || href === '#') return;
        var dates    = j.important_dates || {};
        var lastDate = String(dates.last_date || dates.last_date_to_apply || j.last_date || '').trim();
        var applyMode = (j.apply_mode || '').toLowerCase();

        extra.push({
          title: title,
          slug: href,
          dept: org || String(j.short_information || '').slice(0, 80),
          qual: j.qualification || j.eligibility || '',
          state: j.job_location || j.state || 'All India',
          cat: applyMode === 'offline' ? 'Offline Form' : 'Latest Job',
          tags: [title, org, j.post_name || '',
                 String(j.total_vacancy || ''),
                 String(j.short_information || '').slice(0, 150),
                 'sarkari naukri 2026'].join(' '),
          lastDate: lastDate,
          icon: 'fa-briefcase',
          lastUpdated: j.updated_at || j.last_updated || j.post_date
            || (lastDate ? lastDate + 'T00:00:00' : new Date().toISOString()),
          sectionSource: 'Latest Jobs',
        });
      });

      // sarkariresult_categories
      var srCats = data.sarkariresult_categories || {};
      var SR_META = {
        SR_Latest_Jobs: { cat:'Latest Job',  icon:'fa-briefcase',      label:'SR Latest Jobs' },
        SR_Admit_Card:  { cat:'Admit Card',  icon:'fa-id-card',        label:'Admit Card'     },
        SR_Result:      { cat:'Result',      icon:'fa-trophy',         label:'Result'         },
        SR_Admission:   { cat:'Admission',   icon:'fa-graduation-cap', label:'Admission'      },
        SR_Answer_Key:  { cat:'Answer Key',  icon:'fa-key',            label:'Answer Key'     },
      };
      Object.keys(srCats).forEach(function(key) {
        var m = SR_META[key] || { cat:key, icon:'fa-circle-dot', label:key };
        (Array.isArray(srCats[key]) ? srCats[key] : []).forEach(function(item) {
          var title = String(item.title || item.name || '').trim();
          var href  = item.url || item.link || item.source_url || '';
          if (!title || !href) return;
          extra.push({
            title:title, slug:href,
            dept: item.org || item.organization || '',
            qual:'', state:'', cat:m.cat,
            tags: title + ' ' + m.cat + ' sarkari result 2026',
            lastDate: item.last_date || '',
            icon: m.icon,
            lastUpdated: item.updated_at || new Date().toISOString(),
            sectionSource: m.label,
          });
        });
      });
    }

    /* ── 3. Complete_Jobs_Full_Data.json ────────────────── */
    if (fileName === 'Complete_Jobs_Full_Data.json') {
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        var handledKeys = {};
        Object.keys(COMPLETE_JOBS_META).forEach(function(k){ handledKeys[k] = true; });

        Object.keys(COMPLETE_JOBS_META).forEach(function(catKey) {
          var meta = COMPLETE_JOBS_META[catKey];
          (Array.isArray(data[catKey]) ? data[catKey] : []).forEach(function(job) {
            var title = getJobTitle(job);
            if (!title) return;
            var org  = getJobOrg(job);
            var bd   = job.basic_details || {};
            var href = buildJobHref(job, meta.id);
            var dates = job.important_dates || {};
            var lastDate = String(
              dates.last_date_to_apply || dates.last_date || dates.closing_date || job.last_date || ''
            ).trim();
            extra.push({
              title:title, slug:href,
              dept:org,
              qual: meta.qual || job.qualification || bd.qualification || '',
              state: job.state || 'All India',
              cat: meta.cat,
              tags: [title, job.post_name||'', org, meta.id,
                     String(job.total_vacancies||job.total_vacancy||''),
                     String(bd.short_information||'').slice(0,100),
                     'sarkari job 2026'].join(' '),
              lastDate: lastDate,
              icon: meta.icon,
              lastUpdated: bd.last_updated || job.updated_at || job.last_updated || new Date().toISOString(),
              sectionSource: meta.id,
            });
          });
        });

        // Unknown keys
        Object.keys(data).forEach(function(key) {
          if (handledKeys[key]) return;
          (Array.isArray(data[key]) ? data[key] : []).forEach(function(job) {
            var title = getJobTitle(job);
            if (!title) return;
            var label = key.replace(/_/g, ' ');
            var dates = job.important_dates || {};
            extra.push({
              title:title, slug: buildJobHref(job, label),
              dept: getJobOrg(job),
              qual: job.qualification || '',
              state: job.state || 'All India',
              cat: label,
              tags: title + ' ' + getJobOrg(job) + ' ' + label + ' sarkari naukri',
              lastDate: String(dates.last_date || job.last_date || ''),
              icon: 'fa-briefcase',
              lastUpdated: job.updated_at || job.last_updated || new Date().toISOString(),
              sectionSource: label,
            });
          });
        });
      }
    }

    /* ── 4. state-jobs-data.json ────────────────────────── */
    if (fileName === 'state-jobs-data.json') {
      var sections2 = Array.isArray(data.sections) ? data.sections
        : Array.isArray(data) ? data : [];

      sections2.forEach(function(sec) {
        var secId    = String(sec.id    || sec.title || '').trim();
        var secTitle = String(sec.title || sec.id    || 'State Jobs').trim();
        var secState = String(sec.state || '').trim();

        (sec.items || []).forEach(function(item) {
          var title = String(item.name || item.title || '').trim();
          if (!title) return;

          var detail   = item.detail || {};
          var bd       = detail.basic_details || {};
          var applyMode= (bd.application_mode || '').toLowerCase();
          var href     = item.url || item.link || '';

          var slug = slugifyTitle(bd.job_title || title);
          if (slug && slug !== 'official-link') {
            var prefix = applyMode.indexOf('offline') >= 0 ? 'offline-' : '';
            href = 'job.html?slug=' + encodeURIComponent(prefix + slug)
                 + '&section=' + encodeURIComponent(secId || secTitle);
          }
          if (!href) return;

          var qual = String(
            item.qualification ||
            (detail.qualification && (detail.qualification.education_qualification || '')) ||
            bd.qualification || ''
          ).trim();

          var seoTags = Array.isArray(detail.seo_tags) ? detail.seo_tags.join(' ') : '';
          var board   = String(item.board || bd.organization_name || '').trim();
          var dates2  = detail.important_dates || {};
          var lastDate= String(
            item.lastDate || item.date ||
            dates2.last_date_to_apply || dates2.last_date || ''
          ).replace(/^Last Date:\s*/i, '').trim();

          var luStr = new Date().toISOString();
          if (item.postDate) {
            var p = item.postDate.split('/');
            if (p.length === 3) luStr = p[2] + '-' + p[1] + '-' + p[0] + 'T00:00:00';
          }

          extra.push({
            title:title, slug:href,
            dept: board || secTitle,
            qual: qual,
            state: secState || 'All India',
            cat: 'State Jobs',
            tags: [title, board, secTitle, secState, qual, seoTags,
                   String(bd.short_information||'').slice(0,100),
                   'state jobs sarkari naukri 2026'].join(' '),
            lastDate: lastDate,
            icon: 'fa-location-dot',
            lastUpdated: luStr,
            sectionSource: secTitle,
          });
        });
      });
    }

    return extra;
  }

  /* ══════════════════════════════════════════════════════════
   * CACHE-BUSTING FETCH
   * timestamp query param + cache: 'no-store'
   * ══════════════════════════════════════════════════════════ */
  function cacheBustFetch(fileName) {
    var url = fileName + CFG.cacheBust();
    return fetch(url, {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' },
    }).then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + fileName);
      return r.json();
    });
  }

  /* ── SIMPLE HASH for change detection ───────────────────── */
  function quickHash(data) {
    var str = JSON.stringify(data).slice(0, 5000);
    var h = 0;
    for (var i = 0; i < str.length; i++) {
      h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
    }
    return h;
  }

  /* ── FETCH + PROCESS + MERGE ONE FILE ───────────────────── */
  function fetchAndIndex(fileName, forceRefresh) {
    return cacheBustFetch(fileName)
      .then(function(data) {
        var hash = quickHash(data);
        if (!forceRefresh && lastJsonHashes[fileName] === hash) {
          console.log('[smart-search] No change:', fileName);
          return 0;
        }
        lastJsonHashes[fileName] = hash;

        var extra = processJsonFile(data, fileName);
        console.log('[smart-search]', fileName, '→', extra.length, 'items');

        if (forceRefresh) {
          var newSlugs = {};
          extra.forEach(function(i){ newSlugs[dedupeKey(i.slug)] = true; });
          allData = allData.filter(function(d){ return !newSlugs[dedupeKey(d.slug)]; });
        }

        var changed = mergeItems(extra);
        if (changed) {
          loadFuse(function() {
            buildFuse(allData);
            refreshOpenDropdown();
          });
        }
        return extra.length;
      })
      .catch(function(err) {
        console.warn('[smart-search] ❌ Failed:', fileName, err.message);
        return 0;
      });
  }

  /* ── REFRESH OPEN DROPDOWN ──────────────────────────────── */
  function refreshOpenDropdown() {
    var heroInput = document.getElementById('heroSearch');
    var drop = document.getElementById('tsjDrop');
    if (heroInput && heroInput.value.trim().length >= 1 &&
        drop && drop.classList.contains('open')) {
      heroInput.dispatchEvent(new Event('input'));
    }
  }

  /* ══════════════════════════════════════════════════════════
   * MAIN LOADER — Promise.all() parallel
   *
   * Phase 1 (FAST): dailyupdates + merged_sarkari + state-jobs
   *   parallel load via Promise.all() → ~1-2 sec
   *
   * Phase 2 (HEAVY): Complete_Jobs_Full_Data.json (~18MB)
   *   background after 2 sec
   * ══════════════════════════════════════════════════════════ */
  function loadJsonFiles() {
    console.log('[smart-search] 🚀 Starting parallel JSON load...');

    var fastFiles = [
      'dailyupdates.json',
      'merged_sarkari_data.json',
      'state-jobs-data.json',
    ];

    Promise.all(fastFiles.map(function(f){ return fetchAndIndex(f); }))
      .then(function(counts) {
        searchReady = true;
        var total = counts.reduce(function(a,b){ return a+b; }, 0);
        console.log('[smart-search] ✅ Phase 1 done. Items:', total, 'allData:', allData.length);

        loadFuse(function() {
          buildFuse(allData);
          refreshOpenDropdown();
        });

        // Phase 2: heavy file background
        setTimeout(function() {
          fetchAndIndex('Complete_Jobs_Full_Data.json').then(function(count) {
            console.log('[smart-search] ✅ Phase 2 done. +' + count + ' items. Total:', allData.length);
            buildFuse(allData);
            refreshOpenDropdown();
          });
        }, 2000);
      })
      .catch(function(err) {
        console.error('[smart-search] Phase 1 error:', err);
        searchReady = true;
      });
  }

  /* ══════════════════════════════════════════════════════════
   * AUTO-REFRESH — har 5 min background reload
   * Naya data milne par index update ho
   * ══════════════════════════════════════════════════════════ */
  function startAutoRefresh() {
    setInterval(function() {
      console.log('[smart-search] 🔄 Auto-refresh triggered...');
      var fastFiles = ['dailyupdates.json', 'merged_sarkari_data.json', 'state-jobs-data.json'];
      Promise.all(fastFiles.map(function(f){ return fetchAndIndex(f, true); }))
        .then(function(counts) {
          var anyChanged = counts.some(function(c){ return c > 0; });
          if (anyChanged) {
            buildFuse(allData);
            console.log('[smart-search] 🔄 Auto-refresh: index updated. Total:', allData.length);
          } else {
            console.log('[smart-search] 🔄 Auto-refresh: no changes.');
          }
        });

      setTimeout(function() { fetchAndIndex('Complete_Jobs_Full_Data.json', true); }, 10000);
    }, CFG.refreshIntervalMs);
  }

  /* ── SEARCH ENGINE ──────────────────────────────────────── */
  var STOP_WORDS = {
    'recruitment':1,'2026':1,'2025':1,'2024':1,'apply':1,'online':1,'offline':1,'now':1,'out':1,
    'notification':1,'for':1,'and':1,'the':1,'of':1,'to':1,'in':1,'a':1,'an':1,'is':1,'are':1,'with':1,
    'posts':1,'post':1,'grade':1,'form':1,'exam':1,'test':1,'board':1,'india':1,'all':1,'bharti':1,
    'vacancy':1,'vacancies':1,'jobs':1,'job':1,'latest':1,'new':1,'official':1,'download':1,
  };

  function scoreItem(item, q, queryWords, meaningfulWords) {
    var title = (item.title || '').toLowerCase();
    var tags  = (item.tags  || '').toLowerCase();
    var cat   = (item.cat   || '').toLowerCase();
    var dept  = (item.dept  || '').toLowerCase();
    var sec   = (item.sectionSource || '').toLowerCase();
    var state = (item.state || '').toLowerCase();
    var score = 0;

    if (title.indexOf(q) >= 0) score += 200;
    else if (queryWords.length > 0 && title.indexOf(queryWords[0]) === 0) score += 80;

    var titleHits = 0;
    meaningfulWords.forEach(function(w) {
      if (title.indexOf(w) >= 0) {
        score += w.length >= 5 ? 40 : (w.length >= 3 ? 20 : 8);
        titleHits++;
      }
    });
    if (meaningfulWords.length > 0 && titleHits === meaningfulWords.length) score += 60;

    meaningfulWords.forEach(function(w) {
      if (tags.indexOf(w) >= 0)  score += w.length >= 5 ? 18 : 10;
      if (dept.indexOf(w) >= 0)  score += 10;
      if (cat.indexOf(w) >= 0)   score += 8;
      if (sec.indexOf(w) >= 0)   score += 6;
      if (state.indexOf(w) >= 0) score += 7;
    });

    var allHit = queryWords.every(function(w){ return title.indexOf(w) >= 0; });
    if (allHit && queryWords.length >= 2) score += 50;

    if (titleHits >= 1 && titleHits < meaningfulWords.length) score += 10;
    if (titleHits === 0 && score > 0 && score < 20) score = Math.floor(score * 0.5);

    if (score > 0 && item.lastUpdated) {
      var diffDays = (Date.now() - new Date(item.lastUpdated).getTime()) / 86400000;
      if (diffDays <= 1) score += 30;
      else if (diffDays <= 3) score += 15;
      else if (diffDays <= 7) score += 5;
    }

    return score;
  }

  function doSearch(query) {
    var q = (query || '').trim().toLowerCase();
    if (!q) return [];

    var queryWords = q.split(/\s+/).filter(function(w){ return w.length >= 1; });
    var meaningfulWords = queryWords.filter(function(w){ return w.length >= 2 && !STOP_WORDS[w]; });
    var MIN_SCORE = 3;

    return allData
      .map(function(item) {
        var s = scoreItem(item, q, queryWords, meaningfulWords);
        if (s >= MIN_SCORE) { var c = Object.assign({}, item); c._score = s; return c; }
        return null;
      })
      .filter(Boolean)
      .sort(function(a, b) {
        if (b._score !== a._score) return b._score - a._score;
        var ta = a.lastUpdated ? new Date(a.lastUpdated).getTime() : 0;
        var tb = b.lastUpdated ? new Date(b.lastUpdated).getTime() : 0;
        return tb - ta;
      });
  }

  /* ── INJECT CSS ─────────────────────────────────────────── */
  function injectStyles() {
    if (document.getElementById('tsj-search-styles')) return;
    var style = document.createElement('style');
    style.id = 'tsj-search-styles';
    style.textContent = [
      '#tsjDrop{background:#fff;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 16px 48px rgba(13,34,87,.18);z-index:99999;max-height:420px;overflow-y:auto;display:none;animation:tsjFadeIn .15s ease;scrollbar-width:thin}',
      '#tsjDrop.open{display:block}',
      '@keyframes tsjFadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}',
      '.tsj-suggest-item{display:flex;align-items:center;gap:10px;padding:10px 14px;text-decoration:none;color:#0f172a;border-bottom:1px solid #f8fafc;transition:background .1s;cursor:pointer}',
      '.tsj-suggest-item:last-child{border-bottom:none}',
      '.tsj-suggest-item:hover,.tsj-suggest-item.tsj-active{background:#eff6ff}',
      '.tsj-si-icon{width:30px;height:30px;border-radius:8px;background:#eff6ff;color:#1a56db;display:flex;align-items:center;justify-content:center;font-size:.8rem;flex-shrink:0}',
      '.tsj-si-body{flex:1;overflow:hidden}',
      '.tsj-si-title{display:block;font-size:.83rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.tsj-si-meta{display:block;font-size:.69rem;color:#64748b;margin-top:1px}',
      '.tsj-si-arr{color:#cbd5e1;font-size:.75rem}',
      '.tsj-suggest-item:hover .tsj-si-arr,.tsj-suggest-item.tsj-active .tsj-si-arr{color:#1a56db}',
      'mark.srch-hl{background:#fef08a;color:#92400e;border-radius:2px;padding:0 1px}',
      '.tsj-recent{padding:10px 14px;border-bottom:1px solid #f1f5f9}',
      '.tsj-recent-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:7px;font-size:.72rem;font-weight:800;color:#475569}',
      '.tsj-clear-btn{background:none;border:1px solid #e2e8f0;border-radius:6px;padding:2px 8px;font-size:.68rem;color:#94a3b8;cursor:pointer;font-family:inherit}',
      '.tsj-clear-btn:hover{color:#ef4444;border-color:#ef4444}',
      '.tsj-recent-tags{display:flex;flex-wrap:wrap;gap:5px}',
      '.tsj-recent-tag{background:#f8fafc;color:#475569;border:1px solid #e2e8f0;border-radius:6px;padding:4px 10px;font-size:.72rem;font-weight:600;cursor:pointer;font-family:inherit;transition:all .12s}',
      '.tsj-recent-tag:hover{background:#eff6ff;color:#1a56db;border-color:#bfdbfe}',
      '.tsj-loading-msg{padding:12px 14px;font-size:.8rem;color:#64748b;text-align:center}',
      '.tsj-no-suggest{padding:14px;font-size:.82rem;color:#94a3b8;text-align:center}',
      '.tsj-suggest-footer{display:flex;align-items:center;justify-content:center;gap:6px;padding:9px 14px;font-size:.75rem;font-weight:700;color:#64748b;border-top:1px solid #f1f5f9;background:#fafbfc}',
      '.tsj-badge-pill{display:inline-block;font-size:.62rem;font-weight:700;padding:1px 6px;border-radius:10px;margin-right:2px}',
      '.tsj-b-job{background:#eff6ff;color:#1d4ed8}',
      '.tsj-b-result{background:#f0fdf4;color:#16a34a}',
      '.tsj-b-admit{background:#fef3c7;color:#b45309}',
      '.tsj-b-scheme{background:#fdf4ff;color:#7c3aed}',
      '.tsj-b-link{background:#fff7ed;color:#c2410c}',
      '.tsj-b-other{background:#f1f5f9;color:#475569}',
      '@media(max-width:480px){#tsjDrop{border-radius:10px;max-height:360px}}',
    ].join('');
    document.head.appendChild(style);
  }

  /* ── HERO SEARCH SETUP ──────────────────────────────────── */
  function setupHeroSearch() {
    var input = document.getElementById('heroSearch');
    var btn   = document.getElementById('heroSearchBtn');
    if (!input) return;

    injectStyles();

    // Remove old elements
    ['searchSuggest','heroSearchResults'].forEach(function(id) {
      var el = document.getElementById(id);
      if (el) el.remove();
    });

    var drop = document.getElementById('tsjDrop');
    if (!drop) {
      drop = document.createElement('div');
      drop.id = 'tsjDrop';
      drop.setAttribute('role', 'listbox');
      document.body.appendChild(drop);
    }

    function positionDrop() {
      var rect = (input.closest('.hero-search-box') || input).getBoundingClientRect();
      drop.style.position  = 'fixed';
      drop.style.top       = (rect.bottom + 5) + 'px';
      drop.style.left      = rect.left + 'px';
      drop.style.width     = rect.width + 'px';
      drop.style.maxHeight = '420px';
      drop.style.zIndex    = '99999';
    }
    positionDrop();
    window.addEventListener('resize', positionDrop);
    window.addEventListener('scroll', function() {
      if (drop.classList.contains('open')) positionDrop();
    }, true);

    function openDrop(html) {
      positionDrop();
      drop.innerHTML = html;
      drop.classList.add('open');
      drop.querySelectorAll('.tsj-recent-tag').forEach(function(b) {
        b.addEventListener('click', function() { input.value = b.dataset.q; runSuggest(b.dataset.q); });
      });
      var clearBtn = drop.querySelector('#tsjClearRecent');
      if (clearBtn) {
        clearBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          try { localStorage.removeItem(CFG.recentKey); } catch(e2) {}
          openDrop('<div class="tsj-no-suggest">Type karo search karne ke liye…</div>');
        });
      }
    }

    function closeDrop() {
      drop.classList.remove('open');
      drop.innerHTML = '';
      activeIndex  = -1;
      suggestItems = [];
    }

    function showDefaultDrop() {
      var recent = getRecent();
      if (!recent.length) {
        openDrop('<div class="tsj-no-suggest">Jobs, Results, Admit Cards, Schemes search karo…</div>');
        return;
      }
      openDrop(
        '<div class="tsj-recent">' +
        '<div class="tsj-recent-hd"><span><i class="fa-solid fa-clock-rotate-left"></i> Recent Searches</span>' +
        '<button type="button" id="tsjClearRecent" class="tsj-clear-btn">Clear</button></div>' +
        '<div class="tsj-recent-tags">' +
        recent.map(function(r){ return '<button class="tsj-recent-tag" type="button" data-q="'+esc(r)+'">'+esc(r)+'</button>'; }).join('') +
        '</div></div>');
    }

    function getBadgeClass(cat, sec) {
      var c = ((cat||'') + ' ' + (sec||'')).toLowerCase();
      if (c.indexOf('job')+c.indexOf('latest')+c.indexOf('railway')+c.indexOf('bank')+c.indexOf('police')+c.indexOf('ssc')+c.indexOf('state') > -6) {
        if (/job|latest|railway|bank|police|ssc|state|upsc|defence|teaching|medical|naukri/.test(c)) return 'tsj-b-job';
      }
      if (/result/.test(c)) return 'tsj-b-result';
      if (/admit/.test(c)) return 'tsj-b-admit';
      if (/scheme|yojna|yojana/.test(c)) return 'tsj-b-scheme';
      if (/link|pdf|csc|update/.test(c)) return 'tsj-b-link';
      return 'tsj-b-other';
    }

    function renderSuggestItem(item, q, idx) {
      var active  = idx === activeIndex ? ' tsj-active' : '';
      var sec     = item.sectionSource || item.cat || '';
      var state   = (item.state && item.state !== 'All India') ? item.state : '';
      var bClass  = getBadgeClass(item.cat, sec);

      return '<a class="tsj-suggest-item' + active + '" href="' + esc(item.slug) + '" data-idx="' + idx + '" role="option">' +
        '<span class="tsj-si-icon"><i class="fa-solid ' + esc(item.icon||'fa-briefcase') + '"></i></span>' +
        '<span class="tsj-si-body">' +
          '<span class="tsj-si-title">' + highlight(item.title, q) + '</span>' +
          (sec ? '<span class="tsj-si-meta"><span class="tsj-badge-pill ' + bClass + '">' + esc(sec) + '</span>' + (state ? ' · ' + esc(state) : '') + '</span>' : '') +
        '</span>' +
        '<span class="tsj-si-arr"><i class="fa-solid fa-arrow-right"></i></span>' +
        '</a>';
    }

    function runSuggest(q) {
      q = (q || '').trim();
      if (!q) { showDefaultDrop(); return; }

      var results = doSearch(q).slice(0, CFG.maxSuggest);
      activeIndex  = -1;
      suggestItems = results;

      if (!results.length) {
        if (!searchReady) {
          openDrop('<div class="tsj-loading-msg"><i class="fa-solid fa-spinner fa-spin"></i> Job data load ho raha hai…</div>');
        } else {
          openDrop('<div class="tsj-no-suggest">No results for "<strong>' + esc(q) + '</strong>"<br><small>Try: SSC · Railway · Bank · Police · Result · Haryana</small></div>');
        }
        return;
      }

      var total = doSearch(q).length;
      var footer = total > CFG.maxSuggest
        ? '<div class="tsj-suggest-footer"><i class="fa-solid fa-list"></i> ' + total + ' results found</div>'
        : '';

      openDrop(results.map(function(r, i){ return renderSuggestItem(r, q, i); }).join('') + footer);
    }

    // Keyboard navigation
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
          saveRecent(input.value.trim());
          window.location.href = active.href;
          closeDrop();
        } else if (input.value.trim()) {
          saveRecent(input.value.trim());
          runSuggest(input.value.trim());
        }
      } else if (e.key === 'Escape') {
        closeDrop();
      }
    });

    var debouncedSuggest = debounce(function(q) { runSuggest(q); }, CFG.debounceMs);
    input.addEventListener('input', function() { debouncedSuggest(this.value); });
    input.addEventListener('focus', function() {
      if (this.value.trim().length >= 1) runSuggest(this.value);
      else showDefaultDrop();
    });

    if (btn) {
      btn.addEventListener('click', function() {
        var q = input.value.trim();
        if (!q) return;
        saveRecent(q);
        runSuggest(q);
        input.focus();
      });
    }

    // Click on suggestion
    drop.addEventListener('click', function(e) {
      var item = e.target.closest('.tsj-suggest-item');
      if (item) { saveRecent(input.value.trim()); closeDrop(); }
    });

    // Click outside → close
    document.addEventListener('click', function(e) {
      var box = input.closest('.hero-search-box') || input.parentElement;
      if (!drop.contains(e.target) && !box.contains(e.target)) closeDrop();
    });

    // Mobile button
    var mobileBtn = document.getElementById('mobileSearchBtn');
    if (mobileBtn) {
      mobileBtn.addEventListener('click', function() {
        var hero = document.getElementById('hero-search-section');
        if (hero) { hero.scrollIntoView({ behavior: 'smooth', block: 'start' }); setTimeout(function(){ input.focus(); }, 400); }
      });
    }
  }

  /* ── HEADER SEARCH ──────────────────────────────────────── */
  function setupHeaderSearch() {
    var hInput = document.getElementById('headerSearch');
    var hBtn   = document.getElementById('headerSearchBtn');

    function goToHero(q) {
      var heroInput = document.getElementById('heroSearch');
      var hero = document.getElementById('hero-search-section');
      if (heroInput) {
        if (hero) hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setTimeout(function() {
          heroInput.value = q;
          heroInput.dispatchEvent(new Event('input'));
          heroInput.focus();
        }, 350);
      }
    }

    if (hInput && hBtn) {
      hBtn.addEventListener('click', function() { if (hInput.value.trim()) goToHero(hInput.value.trim()); });
      hInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && hInput.value.trim()) goToHero(hInput.value.trim());
      });
    }

    var openBtn = document.getElementById('openSearchBtn');
    if (openBtn) {
      openBtn.addEventListener('click', function() {
        var heroInput = document.getElementById('heroSearch');
        if (heroInput) {
          var hero = document.getElementById('hero-search-section');
          if (hero) hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
          setTimeout(function(){ heroInput.focus(); }, 350);
        }
      });
    }
  }

  /* ── SEARCH PAGE HANDLER ────────────────────────────────── */
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

      if (pageInput) {
        pageInput.addEventListener('keydown', function(e) {
          if (e.key === 'Enter' && pageInput.value.trim()) {
            var nq = pageInput.value.trim();
            history.replaceState(null, '', 'search.html?q=' + encodeURIComponent(nq));
            saveRecent(nq);
            renderPage(nq);
          }
        });
      }
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
        setTimeout(function() { clearInterval(checkReady); renderPage(q); }, 10000);
      }
    }
  }

  /* ── BLOCK tsjSearchIndex ───────────────────────────────── */
  function installIndexFirewall() {
    var dummy = Array.isArray(window.tsjSearchIndex) ? window.tsjSearchIndex.slice() : [];
    window.tsjSearchIndex = new Proxy(dummy, {
      get: function(t,p){ return t[p]; },
      set: function(t,p,v){ t[p]=v; return true; },
    });
    console.log('[smart-search] 🔒 tsjSearchIndex firewall active.');
  }

  /* ── INIT ───────────────────────────────────────────────── */
  function init() {
    injectStyles();
    installIndexFirewall();
    loadFuse(function(){ buildFuse(allData); });
    loadJsonFiles();
    setupHeroSearch();
    setupHeaderSearch();
    setupSearchPage();
    startAutoRefresh();
    console.log('[smart-search] v3.0 initialized ✅');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
