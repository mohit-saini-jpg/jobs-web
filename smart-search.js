/**
 * ============================================================
 * TOP SARKARI JOBS – ADVANCED SMART SEARCH SYSTEM v2.0
 * Features: Fuzzy search, Fuse.js, Live dropdown, Filters,
 *           Trending tags, Recent searches, Keyboard nav,
 *           Highlight, SEO URLs, Debounce, Lazy JSON loading
 * ============================================================
 */
(function () {
  'use strict';

  /* ── CONFIG ────────────────────────────────────────────── */
  const CFG = {
    fuseJs: 'https://cdnjs.cloudflare.com/ajax/libs/fuse.js/7.0.0/fuse.min.js',
    // ✅ FIXED: Actual JSON files used by this site
    jsonFiles: [
      'merged_sarkari_data.json',
      'dailyupdates.json',
      'Complete_Jobs_Full_Data.json',
      'jobs.json',
    ],
    maxSuggest: 10,
    maxResults: 30,
    debounceMs: 200,
    recentKey: 'tsj_recent_searches',
    maxRecent: 8,
    searchPageUrl: 'search.html',
  };

  /* ── TRENDING TAGS ─────────────────────────────────────── */
  const TRENDING = [
    { label: 'Railway Jobs',   q: 'railway',   icon: 'fa-train' },
    { label: 'Police Jobs',    q: 'police',    icon: 'fa-shield-halved' },
    { label: 'Haryana Jobs',   q: 'haryana',   icon: 'fa-location-dot' },
    { label: '10th Pass Jobs', q: '10th',      icon: 'fa-certificate' },
    { label: 'Admit Card',     q: 'admit card',icon: 'fa-id-card' },
    { label: 'SSC CGL',        q: 'ssc cgl',   icon: 'fa-medal' },
    { label: 'Bank Jobs',      q: 'bank',      icon: 'fa-building-columns' },
    { label: 'Army Jobs',      q: 'army',      icon: 'fa-star' },
    { label: 'Results',        q: 'result',    icon: 'fa-trophy' },
    { label: 'ITI Jobs',       q: 'iti',       icon: 'fa-tools' },
  ];

  /* ── BUILT-IN SEED DATA (fallback when JSON not loaded) ── */
  // ── HELPER: Section slug se readable section name nikaalein ──
  function getSectionName(slug) {
    if (!slug) return 'Other';
    try {
      const url = new URL(slug, 'https://x.com');
      const section = url.searchParams.get('section');
      if (section) return decodeURIComponent(section);
    } catch(e) {}
    // fallback: slug se filename
    const base = slug.split('?')[0].split('/').pop().replace(/\.html?$/i, '');
    return base || 'Other';
  }

  const SEED_DATA = [
    { title: 'SSC CGL 2026', dept: 'Staff Selection Commission', qual: 'Graduation', state: 'All India', cat: 'SSC', tags: 'ssc cgl combined graduate level', slug: 'view.html?section=SSC%20Jobs', lastDate: '', icon: 'fa-medal', lastUpdated: '2026-05-06T10:00:00', sectionSource: 'SSC Jobs' },
    { title: 'SSC CHSL 2026', dept: 'Staff Selection Commission', qual: '12th Pass', state: 'All India', cat: 'SSC', tags: 'ssc chsl 10+2 combined higher secondary', slug: 'view.html?section=SSC%20Jobs', lastDate: '', icon: 'fa-medal', lastUpdated: '2026-05-05T08:00:00', sectionSource: 'SSC Jobs' },
    { title: 'RRB NTPC 2026', dept: 'Railway Recruitment Board', qual: 'Graduation/12th', state: 'All India', cat: 'Railway', tags: 'railway rrb ntpc non technical popular categories', slug: 'view.html?section=Railway%20Jobs', lastDate: '', icon: 'fa-train', lastUpdated: '2026-05-04T12:00:00', sectionSource: 'Railway Jobs' },
    { title: 'RRB Group D', dept: 'Railway Recruitment Board', qual: '10th Pass / ITI', state: 'All India', cat: 'Railway', tags: 'railway rrb group d 10th iti', slug: 'view.html?section=Railway%20Jobs', lastDate: '', icon: 'fa-train', lastUpdated: '2026-05-03T09:00:00', sectionSource: 'Railway Jobs' },
    { title: 'Railway Apprentice 2026', dept: 'Indian Railways', qual: '10th / ITI', state: 'All India', cat: 'Railway', tags: 'railway apprentice 10th iti', slug: 'view.html?section=Railway%20Jobs', lastDate: '', icon: 'fa-train', lastUpdated: '2026-05-02T11:00:00', sectionSource: 'Railway Jobs' },
    { title: 'IBPS PO 2026', dept: 'Institute of Banking Personnel Selection', qual: 'Graduation', state: 'All India', cat: 'Bank', tags: 'ibps po probationary officer bank', slug: 'view.html?section=Bank%20Jobs', lastDate: '', icon: 'fa-building-columns', lastUpdated: '2026-05-01T07:00:00', sectionSource: 'Bank Jobs' },
    { title: 'IBPS Clerk 2026', dept: 'IBPS', qual: 'Graduation', state: 'All India', cat: 'Bank', tags: 'ibps clerk bank banking', slug: 'view.html?section=Bank%20Jobs', lastDate: '', icon: 'fa-building-columns', lastUpdated: '2026-04-30T10:00:00', sectionSource: 'Bank Jobs' },
    { title: 'SBI PO 2026', dept: 'State Bank of India', qual: 'Graduation', state: 'All India', cat: 'Bank', tags: 'sbi po bank probationary officer', slug: 'view.html?section=Bank%20Jobs', lastDate: '', icon: 'fa-building-columns', lastUpdated: '2026-04-29T09:00:00', sectionSource: 'Bank Jobs' },
    { title: 'UP Police Constable 2026', dept: 'UP Police', qual: '12th Pass', state: 'Uttar Pradesh', cat: 'Police', tags: 'police up uttar pradesh constable 12th', slug: 'view.html?section=Police%20Jobs', lastDate: '', icon: 'fa-shield-halved', lastUpdated: '2026-04-28T08:00:00', sectionSource: 'Police Jobs' },
    { title: 'Haryana Police 2026', dept: 'Haryana Police', qual: '12th Pass / Graduation', state: 'Haryana', cat: 'Police', tags: 'haryana police constable si', slug: 'view.html?section=Haryana%20All%20State%20Jobs', lastDate: '', icon: 'fa-shield-halved', lastUpdated: '2026-04-27T14:00:00', sectionSource: 'Haryana All State Jobs' },
    { title: 'HSSC Group D 2026', dept: 'Haryana Staff Selection Commission', qual: '10th / 8th Pass', state: 'Haryana', cat: 'State Jobs', tags: 'haryana hssc group d 10th 8th', slug: 'view.html?section=Haryana%20All%20State%20Jobs', lastDate: '', icon: 'fa-location-dot', lastUpdated: '2026-04-26T10:00:00', sectionSource: 'Haryana All State Jobs' },
    { title: 'Haryana CET 2026', dept: 'HSSC', qual: 'Graduation / 10th', state: 'Haryana', cat: 'State Jobs', tags: 'haryana cet common eligibility test hssc', slug: 'view.html?section=Haryana%20All%20State%20Jobs', lastDate: '', icon: 'fa-location-dot', lastUpdated: '2026-04-25T09:00:00', sectionSource: 'Haryana All State Jobs' },
    { title: 'Indian Army Agniveer 2026', dept: 'Indian Army', qual: '10th / 12th Pass', state: 'All India', cat: 'Defence', tags: 'army agniveer defence 10th 12th soldier', slug: 'view.html?section=Defence%20Jobs', lastDate: '', icon: 'fa-star', lastUpdated: '2026-04-24T11:00:00', sectionSource: 'Defence Jobs' },
    { title: 'Indian Navy Agniveer 2026', dept: 'Indian Navy', qual: '10th / 12th Pass', state: 'All India', cat: 'Defence', tags: 'navy agniveer defence 10th 12th', slug: 'view.html?section=Defence%20Jobs', lastDate: '', icon: 'fa-star', lastUpdated: '2026-04-23T08:00:00', sectionSource: 'Defence Jobs' },
    { title: 'CRPF Constable 2026', dept: 'CRPF', qual: '10th Pass', state: 'All India', cat: 'Police', tags: 'crpf constable police 10th central', slug: 'view.html?section=Police%20Jobs', lastDate: '', icon: 'fa-shield-halved', lastUpdated: '2026-04-22T10:00:00', sectionSource: 'Police Jobs' },
    { title: 'UPSC Civil Services 2026', dept: 'UPSC', qual: 'Graduation', state: 'All India', cat: 'UPSC', tags: 'upsc ias ips civil services exam', slug: 'view.html?section=UPSC%20Jobs', lastDate: '', icon: 'fa-graduation-cap', lastUpdated: '2026-04-21T09:00:00', sectionSource: 'UPSC Jobs' },
    { title: 'NTA NEET 2026', dept: 'NTA', qual: '12th Pass (PCB)', state: 'All India', cat: 'Admissions', tags: 'neet medical admission mbbs 12th', slug: 'view.html?section=Admissions', lastDate: '', icon: 'fa-stethoscope', lastUpdated: '2026-04-20T12:00:00', sectionSource: 'Admissions' },
    { title: 'JEE Main 2026', dept: 'NTA', qual: '12th Pass (PCM)', state: 'All India', cat: 'Admissions', tags: 'jee main engineering admission b.tech 12th', slug: 'view.html?section=Admissions', lastDate: '', icon: 'fa-microchip', lastUpdated: '2026-04-19T10:00:00', sectionSource: 'Admissions' },
    { title: 'Bihar Police 2026', dept: 'Bihar Police', qual: '12th Pass', state: 'Bihar', cat: 'Police', tags: 'bihar police constable 12th', slug: 'view.html?section=State%20jobs', lastDate: '', icon: 'fa-shield-halved', lastUpdated: '2026-04-18T08:00:00', sectionSource: 'State Jobs' },
    { title: 'Rajasthan Police 2026', dept: 'Rajasthan Police', qual: '10th / 12th Pass', state: 'Rajasthan', cat: 'Police', tags: 'rajasthan police constable 10th 12th', slug: 'view.html?section=State%20jobs', lastDate: '', icon: 'fa-shield-halved', lastUpdated: '2026-04-17T09:00:00', sectionSource: 'State Jobs' },
    { title: 'RPSC RAS 2026', dept: 'Rajasthan PSC', qual: 'Graduation', state: 'Rajasthan', cat: 'State Jobs', tags: 'rpsc ras rajasthan administrative service graduation', slug: 'view.html?section=State%20jobs', lastDate: '', icon: 'fa-briefcase', lastUpdated: '2026-04-16T11:00:00', sectionSource: 'State Jobs' },
    { title: 'Teacher Recruitment 2026', dept: 'Various State Boards', qual: 'B.Ed / D.El.Ed', state: 'All India', cat: 'Teaching', tags: 'teacher teaching primary tgt pgt bed stet ctet', slug: 'view.html?section=Teaching%20Jobs', lastDate: '', icon: 'fa-chalkboard-teacher', lastUpdated: '2026-04-15T10:00:00', sectionSource: 'Teaching Jobs' },
    { title: 'CTET 2026', dept: 'CBSE', qual: 'B.Ed / D.El.Ed', state: 'All India', cat: 'Teaching', tags: 'ctet teacher teaching eligibility test cbse bed', slug: 'view.html?section=Teaching%20Jobs', lastDate: '', icon: 'fa-chalkboard-teacher', lastUpdated: '2026-04-14T09:00:00', sectionSource: 'Teaching Jobs' },
    { title: 'Driver Recruitment 2026', dept: 'Various Depts', qual: '8th / 10th Pass', state: 'All India', cat: 'Others', tags: 'driver 8th 10th pass vehicle government', slug: 'view.html?section=latest%20jobs', lastDate: '', icon: 'fa-car', lastUpdated: '2026-04-13T08:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Clerk Recruitment 2026', dept: 'Various Depts', qual: '12th / Graduation', state: 'All India', cat: 'Others', tags: 'clerk 12th graduation office assistant', slug: 'view.html?section=latest%20jobs', lastDate: '', icon: 'fa-briefcase', lastUpdated: '2026-04-12T12:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Anganwadi Workers 2026', dept: 'Women & Child Development', qual: '8th / 10th Pass', state: 'All India', cat: 'Others', tags: 'anganwadi worker helper 8th 10th women', slug: 'view.html?section=latest%20jobs', lastDate: '', icon: 'fa-heart', lastUpdated: '2026-04-11T10:00:00', sectionSource: 'Latest Jobs' },
    { title: 'ITI Apprentice 2026', dept: 'Various PSUs', qual: 'ITI Pass', state: 'All India', cat: 'ITI Jobs', tags: 'iti apprentice technician trade', slug: 'view.html?section=ITI%20Pass%20jobs', lastDate: '', icon: 'fa-tools', lastUpdated: '2026-04-10T09:00:00', sectionSource: 'ITI Pass Jobs' },
    { title: 'ONGC Recruitment 2026', dept: 'ONGC', qual: 'ITI / Diploma / B.Tech', state: 'All India', cat: 'PSU', tags: 'ongc psu oil gas iti diploma engineer', slug: 'view.html?section=latest%20jobs', lastDate: '', icon: 'fa-industry', lastUpdated: '2026-04-09T11:00:00', sectionSource: 'Latest Jobs' },
    { title: 'BSNL JE 2026', dept: 'BSNL', qual: 'Diploma / B.Tech', state: 'All India', cat: 'Telecom', tags: 'bsnl je junior engineer telecom diploma btech', slug: 'view.html?section=latest%20jobs', lastDate: '', icon: 'fa-tower-broadcast', lastUpdated: '2026-04-08T08:00:00', sectionSource: 'Latest Jobs' },
    { title: 'MP Police 2026', dept: 'MP Police', qual: '12th Pass', state: 'Madhya Pradesh', cat: 'Police', tags: 'mp madhya pradesh police constable 12th', slug: 'view.html?section=State%20jobs', lastDate: '', icon: 'fa-shield-halved', lastUpdated: '2026-04-07T10:00:00', sectionSource: 'State Jobs' },
    { title: 'BPSC 2026', dept: 'Bihar PSC', qual: 'Graduation', state: 'Bihar', cat: 'State Jobs', tags: 'bpsc bihar psc state civil services graduation', slug: 'view.html?section=State%20jobs', lastDate: '', icon: 'fa-briefcase', lastUpdated: '2026-04-06T09:00:00', sectionSource: 'State Jobs' },
    { title: 'SSC MTS 2026', dept: 'Staff Selection Commission', qual: '10th Pass', state: 'All India', cat: 'SSC', tags: 'ssc mts multi tasking staff 10th pass', slug: 'view.html?section=SSC%20Jobs', lastDate: '', icon: 'fa-medal', lastUpdated: '2026-04-05T11:00:00', sectionSource: 'SSC Jobs' },
    { title: 'SSC GD Constable 2026', dept: 'SSC / CAPF', qual: '10th Pass', state: 'All India', cat: 'SSC', tags: 'ssc gd constable 10th pass capf paramilitary', slug: 'view.html?section=SSC%20Jobs', lastDate: '', icon: 'fa-medal', lastUpdated: '2026-04-04T08:00:00', sectionSource: 'SSC Jobs' },
    { title: 'Post Office GDS 2026', dept: 'India Post', qual: '10th Pass', state: 'All India', cat: 'Postal', tags: 'post office gds gramin dak sevak 10th pass', slug: 'view.html?section=latest%20jobs', lastDate: '', icon: 'fa-envelope', lastUpdated: '2026-04-03T10:00:00', sectionSource: 'Latest Jobs' },
    { title: 'AIIMS Nursing 2026', dept: 'AIIMS', qual: 'B.Sc Nursing', state: 'All India', cat: 'Medical', tags: 'aiims nursing nurse medical hospital healthcare', slug: 'view.html?section=Medical%2F%20Healthcare%20Jobs', lastDate: '', icon: 'fa-stethoscope', lastUpdated: '2026-04-02T09:00:00', sectionSource: 'Medical / Healthcare Jobs' },
  ];

  /* ── STATE ──────────────────────────────────────────────── */
  let fuseInstance = null;
  let allData = [...SEED_DATA];
  let activeIndex = -1;
  let suggestItems = [];
  let currentFilters = { qual: '', state: '', cat: '', sort: 'latest' };
  let fuseLoaded = false;
  let jsonIndexReady = false;   // ✅ true after all JSON files loaded

  /* ── UTILS ──────────────────────────────────────────────── */
  function esc(s) {
    return String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  function debounce(fn, ms) {
    let t; return function (...a) { clearTimeout(t); t = setTimeout(() => fn.apply(this, a), ms); };
  }

  function highlight(text, query) {
    if (!query || !text) return esc(text);
    const words = query.trim().split(/\s+/).filter(w => w.length > 1);
    let result = esc(text);
    words.forEach(w => {
      const rx = new RegExp('(' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      result = result.replace(rx, '<mark class="srch-hl">$1</mark>');
    });
    return result;
  }

  /* ── RECENT SEARCHES ────────────────────────────────────── */
  function getRecent() {
    try { return JSON.parse(localStorage.getItem(CFG.recentKey) || '[]'); } catch { return []; }
  }
  function saveRecent(q) {
    if (!q || q.length < 2) return;
    let list = getRecent().filter(r => r.toLowerCase() !== q.toLowerCase());
    list.unshift(q);
    list = list.slice(0, CFG.maxRecent);
    try { localStorage.setItem(CFG.recentKey, JSON.stringify(list)); } catch {}
  }

  /* ── LOAD FUSE.JS DYNAMICALLY ───────────────────────────── */
  function loadFuse(cb) {
    if (window.Fuse) { cb(); return; }
    const s = document.createElement('script');
    s.src = CFG.fuseJs;
    s.onload = cb;
    s.onerror = cb; // gracefully fall back to built-in search
    document.head.appendChild(s);
  }

  function buildFuse(data) {
    if (!window.Fuse) return;
    fuseInstance = new window.Fuse(data, {
      keys: [
        { name: 'title',  weight: 0.5 },
        { name: 'tags',   weight: 0.25 },
        { name: 'cat',    weight: 0.1 },
        { name: 'dept',   weight: 0.08 },
        { name: 'state',  weight: 0.04 },
        { name: 'qual',   weight: 0.03 },
      ],
      threshold: 0.5,          // ✅ FIX: 0.45→0.5, single word bhi match hoga
      includeScore: true,
      ignoreLocation: true,
      minMatchCharLength: 1,  // ✅ FIX: 1 word/char se bhi search ho
    });
    fuseLoaded = true;
  }

  
  /* ── LOAD JSON FILES ────────────────────────────────────── */
  /*
   * Uses EXACT same parsing as script.js + job.html — verified field names:
   *
   * merged_sarkari_data.json:
   *   .jobs[]                     → {title, slug, apply_mode, organization,
   *                                   important_dates:{last_date}}
   *   .sarkariresultshine_jobs[]  → {title, source_url, organization, last_date}
   *   .sarkariresult_categories   → {SR_Latest_Jobs:[{title,url}], ...}
   *
   * dailyupdates.json:
   *   .sections[]                 → {title, id, icon, items:[{name, url, slug, date}]}
   *
   * Complete_Jobs_Full_Data.json:
   *   {Railway_Jobs:[...], Bank_Jobs:[...], ...}
   *   Each item: {title, slug, organization, basic_details:{job_title,organization_name},
   *               important_dates:{last_date}, total_vacancy, apply_mode}
   */

  /* Category meta for Complete_Jobs_Full_Data.json keys */
  const COMPLETE_JOBS_META = {
    Latest_Notifications: { id:'Latest Notifications',   icon:'fa-bell',             qual:'',               cat:'Latest'     },
    '10TH_Pass':          { id:'10th Pass Jobs',          icon:'fa-graduation-cap',   qual:'10th Pass',      cat:'State Jobs' },
    '8TH_Pass':           { id:'8th Pass Jobs',           icon:'fa-book',             qual:'8th Pass',       cat:'State Jobs' },
    '12TH_Pass':          { id:'12th Pass Jobs',          icon:'fa-graduation-cap',   qual:'12th Pass',      cat:'State Jobs' },
    Diploma:              { id:'Diploma Jobs',            icon:'fa-scroll',           qual:'Diploma',        cat:'Others'     },
    ITI:                  { id:'ITI Jobs',                icon:'fa-tools',            qual:'ITI',            cat:'ITI Jobs'   },
    B_Tech_BE:            { id:'B.Tech Jobs',             icon:'fa-microchip',        qual:'B.Tech',         cat:'Engineering'},
    B_Com:                { id:'B.Com Jobs',              icon:'fa-chart-line',       qual:'B.Com',          cat:'Others'     },
    Any_Graduate:         { id:'Graduation Jobs',         icon:'fa-university',       qual:'Graduation',     cat:'Others'     },
    Any_Post_Graduate:    { id:'Post Graduation Jobs',    icon:'fa-user-tie',         qual:'Post Graduation',cat:'Others'     },
    Railway_Jobs:         { id:'Railway Jobs',            icon:'fa-train',            qual:'',               cat:'Railway'    },
    Police_Defence:       { id:'Police Jobs',             icon:'fa-shield-halved',    qual:'',               cat:'Police'     },
    Teaching_Faculty:     { id:'Teaching Jobs',           icon:'fa-chalkboard-user',  qual:'B.Ed',           cat:'Teaching'   },
    Bank_Jobs:            { id:'Bank Jobs',               icon:'fa-building-columns', qual:'Graduation',     cat:'Bank'       },
    Medical_Hospital:     { id:'Medical Jobs',            icon:'fa-stethoscope',      qual:'',               cat:'Medical'    },
    Last_Date_Reminder:   { id:'Last Date Reminder',      icon:'fa-clock',            qual:'',               cat:'Latest'     },
    SSC_Jobs:             { id:'SSC Jobs',                icon:'fa-medal',            qual:'',               cat:'SSC'        },
    UPSC_Jobs:            { id:'UPSC Jobs',               icon:'fa-graduation-cap',   qual:'Graduation',     cat:'UPSC'       },
    Haryana_Jobs:         { id:'Haryana Jobs',            icon:'fa-location-dot',     qual:'',               cat:'State Jobs' },
    Defence_Jobs:         { id:'Defence Jobs',            icon:'fa-star',             qual:'',               cat:'Defence'    },
  };

  /* Exact same slugify as script.js slugifyForJob */
  function slugifyTitle(raw) {
    return String(raw || '')
      .normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
      .replace(/&/g, ' and ').replace(/['']/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .replace(/-{2,}/g, '-')
      .slice(0, 120) || 'official-link';
  }

  /* Build job.html href from a job object — same as index.html jobHref() */
  function buildJobHref(job, secId) {
    const slug = job.slug || slugifyTitle(
      job.title || job.post_name ||
      (job.basic_details && (job.basic_details.job_title || job.basic_details.post_name)) || ''
    );
    if (!slug || slug === 'official-link') return job.source_url || job.url || job.link || '#';
    const prefix = (job.apply_mode || '').toLowerCase() === 'offline' ? 'offline-' : '';
    return 'job.html?slug=' + encodeURIComponent(prefix + slug) +
           (secId ? '&section=' + encodeURIComponent(secId) : '');
  }

  /* Extract title from a job object — same priority as job.html parseFullJob */
  function getJobTitle(job) {
    const bd = job.basic_details || {};
    return String(
      job.title || job.post_name ||
      bd.job_title || bd.post_name || ''
    ).trim();
  }

  /* Extract org from a job object */
  function getJobOrg(job) {
    const bd = job.basic_details || {};
    return String(
      job.organization || job.board_name || job.department ||
      bd.organization_name || bd.department || ''
    ).trim();
  }

  async function loadJsonFiles() {
    let fetchResults;
    try {
      fetchResults = await Promise.allSettled(
        CFG.jsonFiles.map(f =>
          fetch(f)
            .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
            .catch(() => null)
        )
      );
    } catch (e) {
      fetchResults = [];
    }

    const extra = [];
    let totalLoaded = 0;

    fetchResults.forEach((res, idx) => {
      if (res.status !== 'fulfilled' || !res.value) {
        console.warn('[smart-search] Failed to load:', CFG.jsonFiles[idx]);
        return;
      }
      const data = res.value;
      const fileName = CFG.jsonFiles[idx];
      let count = 0;

      /* ══════════════════════════════════════════════════════
         1.  merged_sarkari_data.json
         Structure: { jobs:[], sarkariresultshine_jobs:[],
                      sarkariresult_categories:{SR_*:[]} }
      ══════════════════════════════════════════════════════ */
      if (fileName === 'merged_sarkari_data.json') {

        /* A. jobs[] — main array with full job objects */
        const mainJobs = Array.isArray(data.jobs) ? data.jobs : [];
        mainJobs.forEach(j => {
          const title = getJobTitle(j);
          if (!title) return;
          const org  = getJobOrg(j);
          const href = buildJobHref(j, 'Latest Jobs');
          const lastDate = (j.important_dates
            ? (j.important_dates.last_date || j.important_dates.last_date_to_apply || '')
            : '') || j.last_date || '';
          const applyMode = (j.apply_mode || '').toLowerCase();
          extra.push({
            title, slug: href,
            dept: org,
            qual: j.qualification || '',
            state: j.state || 'All India',
            cat: applyMode === 'offline' ? 'Offline Form' : 'Latest Job',
            tags: title + ' ' + org + ' ' + (j.total_vacancy || '') + ' sarkari naukri 2026',
            lastDate,
            icon: 'fa-briefcase',
            lastUpdated: j.updated_at || j.last_updated || new Date().toISOString(),
            sectionSource: 'Latest Jobs',
          });
          count++;
        });

        /* B. sarkariresultshine_jobs[] */
        const shineJobs = Array.isArray(data.sarkariresultshine_jobs) ? data.sarkariresultshine_jobs : [];
        shineJobs.forEach(j => {
          const title = getJobTitle(j);
          if (!title) return;
          const org  = getJobOrg(j);
          const href = j.source_url || j.url || j.link || buildJobHref(j, 'SR Latest Jobs');
          if (!href || href === '#') return;
          const lastDate = (j.important_dates
            ? (j.important_dates.last_date || '')
            : '') || j.last_date || '';
          extra.push({
            title, slug: href,
            dept: org,
            qual: '', state: '',
            cat: 'Latest Job',
            tags: title + ' ' + org + ' sarkari result naukri',
            lastDate,
            icon: 'fa-briefcase',
            lastUpdated: j.updated_at || new Date().toISOString(),
            sectionSource: 'Sarkari Result',
          });
          count++;
        });

        /* C. sarkariresult_categories — SR_Latest_Jobs, SR_Admit_Card, etc. */
        const srCats = data.sarkariresult_categories || {};
        const SR_META = {
          SR_Latest_Jobs: { cat:'Latest Job',  icon:'fa-briefcase',      label:'SR Latest Jobs' },
          SR_Admit_Card:  { cat:'Admit Card',  icon:'fa-id-card',        label:'SR Admit Card'  },
          SR_Result:      { cat:'Result',      icon:'fa-trophy',         label:'SR Result'      },
          SR_Admission:   { cat:'Admission',   icon:'fa-graduation-cap', label:'SR Admission'   },
          SR_Answer_Key:  { cat:'Answer Key',  icon:'fa-key',            label:'SR Answer Key'  },
        };
        Object.keys(srCats).forEach(key => {
          const m   = SR_META[key] || { cat: key, icon: 'fa-circle-dot', label: key };
          const arr = Array.isArray(srCats[key]) ? srCats[key] : [];
          arr.forEach(item => {
            const title = String(item.title || item.name || '').trim();
            const href  = item.url || item.link || item.source_url || '';
            if (!title || !href) return;
            extra.push({
              title, slug: href,
              dept: item.org || item.organization || '',
              qual: '', state: '',
              cat: m.cat,
              tags: title + ' ' + m.cat + ' sarkari result 2026',
              lastDate: item.last_date || '',
              icon: m.icon,
              lastUpdated: item.updated_at || new Date().toISOString(),
              sectionSource: m.label,
            });
            count++;
          });
        });
      }

      /* ══════════════════════════════════════════════════════
         2.  dailyupdates.json
         Structure: { sections:[{title, id, icon, items:[{name, url, slug, date}]}] }
         (confirmed by job.html line 1366: Array.isArray(dailyRaw.sections))
      ══════════════════════════════════════════════════════ */
      if (fileName === 'dailyupdates.json') {
        /* Support both {sections:[]} and top-level array */
        const sections = Array.isArray(data.sections) ? data.sections
          : Array.isArray(data) ? data : [];

        sections.forEach(sec => {
          const secId    = String(sec.id    || sec.title || '').trim();
          const secTitle = String(sec.title || sec.id    || 'Update').trim();
          const secIcon  = (String(sec.icon || 'fa-bell')).replace(/^fa-solid\s+/, '');

          (sec.items || []).forEach(item => {
            const title = String(item.name || item.title || '').trim();
            if (!title) return;

            /* href: slug → job.html, else url/link */
            let href = '';
            if (item.slug) {
              href = 'job.html?slug=' + encodeURIComponent(item.slug)
                   + '&section=' + encodeURIComponent(secId || secTitle);
            } else {
              href = item.url || item.link || '';
            }
            if (!href) return;

            extra.push({
              title, slug: href,
              dept: secTitle,
              qual: '', state: '',
              cat: secTitle,
              tags: title + ' ' + secTitle + ' sarkari 2026',
              lastDate: item.date || item.last_date || '',
              icon: secIcon,
              lastUpdated: item.updated_at || item.last_updated || new Date().toISOString(),
              sectionSource: secTitle,
            });
            count++;
          });
        });
      }

      /* ══════════════════════════════════════════════════════
         3.  Complete_Jobs_Full_Data.json
         Structure: { Railway_Jobs:[...], Bank_Jobs:[...], ... }
         Each item: { title, slug, organization, apply_mode,
                      basic_details:{job_title, organization_name},
                      important_dates:{last_date, last_date_to_apply} }
         (verified from job.html parseFullJob + _JOBS_CAT_META_JI)
      ══════════════════════════════════════════════════════ */
      if (fileName === 'Complete_Jobs_Full_Data.json') {
        if (data && typeof data === 'object' && !Array.isArray(data)) {

          /* Handle known category keys first */
          const handledKeys = new Set(Object.keys(COMPLETE_JOBS_META));

          /* Process known categories */
          Object.entries(COMPLETE_JOBS_META).forEach(([catKey, meta]) => {
            const jobs = Array.isArray(data[catKey]) ? data[catKey] : [];
            jobs.forEach(job => {
              const title = getJobTitle(job);
              if (!title) return;
              const org  = getJobOrg(job);
              const href = buildJobHref(job, meta.id);
              const dates = job.important_dates || {};
              const lastDate = (
                dates.last_date_to_apply || dates.last_date ||
                dates.closing_date || job.last_date || ''
              ).toString().trim();
              extra.push({
                title, slug: href,
                dept: org,
                qual: meta.qual || job.qualification || '',
                state: job.state || 'All India',
                cat: meta.cat,
                tags: title + ' ' + org + ' ' + meta.id
                    + ' ' + (job.total_vacancy || '') + ' sarkari job 2026',
                lastDate,
                icon: meta.icon,
                lastUpdated: job.updated_at || job.last_updated || job.created_at || new Date().toISOString(),
                sectionSource: meta.id,
              });
              count++;
            });
          });

          /* Process any remaining unknown keys */
          Object.keys(data).forEach(key => {
            if (handledKeys.has(key)) return;
            const arr = Array.isArray(data[key]) ? data[key] : [];
            arr.forEach(job => {
              const title = getJobTitle(job);
              if (!title) return;
              const org  = getJobOrg(job);
              const label = key.replace(/_/g, ' ');
              const href  = buildJobHref(job, label);
              const dates = job.important_dates || {};
              const lastDate = (
                dates.last_date_to_apply || dates.last_date ||
                dates.closing_date || job.last_date || ''
              ).toString().trim();
              extra.push({
                title, slug: href,
                dept: org,
                qual: job.qualification || '',
                state: job.state || 'All India',
                cat: label,
                tags: title + ' ' + org + ' ' + label + ' sarkari naukri',
                lastDate,
                icon: 'fa-briefcase',
                lastUpdated: job.updated_at || job.last_updated || new Date().toISOString(),
                sectionSource: label,
              });
              count++;
            });
          });
        }
      }

      /* ══════════════════════════════════════════════════════
         4.  jobs.json  (legacy — flat arrays + sections)
      ══════════════════════════════════════════════════════ */
      if (fileName === 'jobs.json') {
        ['top_jobs','left_jobs','right_jobs','jobs','latest_jobs','items'].forEach(key => {
          if (!Array.isArray(data[key])) return;
          data[key].forEach(item => {
            const title = String(item.name || item.title || '').trim();
            const href  = item.url || item.link || item.slug || '';
            if (!title || !href) return;
            extra.push({
              title, slug: href,
              dept: item.department || item.dept || '',
              qual: item.qualification || item.qual || '',
              state: item.state || '',
              cat: item.category || item.cat || 'Latest',
              tags: [title, item.tags, item.keywords].filter(Boolean).join(' '),
              lastDate: item.last_date || item.lastDate || '',
              icon: item.icon || 'fa-briefcase',
              lastUpdated: item.last_updated || item.updated_at || new Date().toISOString(),
              sectionSource: item.section || item.source || getSectionName(href),
            });
            count++;
          });
        });
        if (Array.isArray(data.sections)) {
          data.sections.forEach(sec => {
            (sec.items || []).forEach(item => {
              const title = String(item.name || item.title || '').trim();
              const href  = item.url || item.link || '';
              if (!title || !href) return;
              extra.push({
                title, slug: href,
                dept: sec.title || '',
                qual: '', state: '',
                cat: sec.category || sec.title || '',
                tags: title + ' ' + (sec.title || ''),
                lastDate: item.last_date || '',
                icon: 'fa-file-alt',
                lastUpdated: item.last_updated || sec.updated_at || new Date().toISOString(),
                sectionSource: sec.title || getSectionName(href),
              });
              count++;
            });
          });
        }
      }

      totalLoaded += count;
      console.log('[smart-search]', fileName, '→', count, 'items indexed');
    });

    /* Merge into allData (deduplicate by slug URL) */
    if (extra.length) {
      const seen = new Set(allData.map(d => d.slug));
      extra.forEach(item => {
        if (!seen.has(item.slug)) { seen.add(item.slug); allData.push(item); }
      });
    }

    jsonIndexReady = true;
    console.log('[smart-search] ✅ Index ready. Total items:', allData.length,
      '(SEED:', SEED_DATA.length, '+ JSON:', totalLoaded, ')');
    loadFuse(() => {
      buildFuse(allData);
      // ✅ FIX: JSON load ke baad agar user ne kuch type kar rakha hai to suggestion refresh karo
      const heroInput = document.getElementById('heroSearch');
      if (heroInput && heroInput.value.trim().length >= 1) {
        const drop = document.getElementById('tsjDrop');
        if (drop && drop.classList.contains('open')) {
          // showSuggest already bound — trigger input event to refresh
          heroInput.dispatchEvent(new Event('input'));
        }
      }
    });
  }

    /* ── SORT BY LAST UPDATED (descending) ─────────────────── */
  function sortByLastUpdated(results) {
    return results.slice().sort((a, b) => {
      const ta = a.lastUpdated ? new Date(a.lastUpdated).getTime() : 0;
      const tb = b.lastUpdated ? new Date(b.lastUpdated).getTime() : 0;
      return tb - ta; // newest first
    });
  }

  /* ── FORMAT RELATIVE TIME ───────────────────────────────── */
  function relativeTime(dateStr) {
    if (!dateStr) return null;
    const d = new Date(dateStr);
    if (isNaN(d)) return null;
    const now = Date.now();
    const diff = now - d.getTime();
    const mins  = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days  = Math.floor(diff / 86400000);
    if (mins < 1)   return 'अभी';
    if (mins < 60)  return `${mins} मिनट पहले`;
    if (hours < 24) return `${hours} घंटे पहले`;
    if (days < 7)   return `${days} दिन पहले`;
    return d.toLocaleDateString('hi-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  /* ── SEARCH ENGINE ──────────────────────────────────────── */
  function doSearch(query, filters = {}) {
    const q = (query || '').trim().toLowerCase();
    if (!q) return [];

    let results;

    // ✅ FIX: Single char (≤2) ke liye seedha includes match — Fuse short strings mein weak hai
    if (q.length <= 2) {
      results = allData
        .map(item => {
          const hay = (item.title + ' ' + item.tags + ' ' + item.cat + ' ' + item.dept + ' ' + item.state).toLowerCase();
          const score = hay.includes(q) ? (item.title.toLowerCase().startsWith(q) ? 20 : 10) : 0;
          return { ...item, _score: score };
        })
        .filter(r => r._score > 0)
        .sort((a, b) => b._score - a._score);
    } else if (fuseLoaded && fuseInstance) {
      results = fuseInstance.search(q, { limit: 50 }).map(r => r.item);
    } else {
      // Fallback built-in search — single word bhi match kare
      results = allData
        .map(item => {
          const hay = (item.title + ' ' + item.tags + ' ' + item.cat + ' ' + item.dept + ' ' + item.state).toLowerCase();
          let score = 0;
          q.split(/\s+/).forEach(word => {
            if (word.length === 0) return;
            if (hay.includes(word)) score += word.length >= 3 ? 10 : 6;  // ✅ FIX: single char words bhi match
          });
          if (item.title.toLowerCase().includes(q)) score += 15;
          if (item.cat.toLowerCase().includes(q)) score += 5;
          return { ...item, _score: score };
        })
        .filter(r => r._score > 0)
        .sort((a, b) => b._score - a._score);
    }

    // Apply filters
    if (filters.qual) results = results.filter(r => r.qual.toLowerCase().includes(filters.qual.toLowerCase()));
    if (filters.state) results = results.filter(r => r.state.toLowerCase().includes(filters.state.toLowerCase()) || r.state === 'All India');
    if (filters.cat) results = results.filter(r => r.cat.toLowerCase().includes(filters.cat.toLowerCase()));

    // Sort by lastUpdated descending (newly updated → top)
    results = sortByLastUpdated(results);

    return results;
  }

  /* ── RENDER SUGGESTION ITEM ─────────────────────────────── */
  function renderSuggestItem(item, query, idx) {
    return `
      <a class="tsj-suggest-item${idx === activeIndex ? ' tsj-active' : ''}" 
         href="${esc(item.slug)}" 
         data-idx="${idx}" 
         role="option"
         aria-selected="${idx === activeIndex}">
        <span class="tsj-si-icon"><i class="fa-solid ${esc(item.icon || 'fa-briefcase')}"></i></span>
        <span class="tsj-si-body">
          <span class="tsj-si-title">${highlight(item.title, query)}</span>
          ${(item.sectionSource || item.cat) ? `<span class="tsj-si-meta">${esc(item.sectionSource || item.cat)}${item.state && item.state !== 'All India' ? ' · ' + esc(item.state) : ''}</span>` : ''}
        </span>
        <span class="tsj-si-arr"><i class="fa-solid fa-arrow-right"></i></span>
      </a>`;
  }

  /* ── RENDER RESULT CARD ─────────────────────────────────── */
  function renderResultCard(item, query) {
    const slug = item.slug || '#';
    const relTime = relativeTime(item.lastUpdated);
    const sectionLabel = item.sectionSource || getSectionName(item.slug);
    return `
      <div class="tsj-result-card">
        <div class="tsj-rc-head">
          <span class="tsj-rc-icon" aria-hidden="true"><i class="fa-solid ${esc(item.icon || 'fa-briefcase')}"></i></span>
          <div class="tsj-rc-info">
            <a class="tsj-rc-title" href="${esc(slug)}">${highlight(item.title, query)}</a>
            ${item.dept ? `<div class="tsj-rc-dept">${esc(item.dept)}</div>` : ''}
          </div>
        </div>
        <div class="tsj-rc-tags">
          ${item.qual ? `<span class="tsj-tag tsj-tag-qual"><i class="fa-solid fa-graduation-cap"></i> ${esc(item.qual)}</span>` : ''}
          ${item.state ? `<span class="tsj-tag tsj-tag-state"><i class="fa-solid fa-location-dot"></i> ${esc(item.state)}</span>` : ''}
          ${item.cat ? `<span class="tsj-tag tsj-tag-cat">${esc(item.cat)}</span>` : ''}
          ${item.lastDate ? `<span class="tsj-tag tsj-tag-date"><i class="fa-solid fa-clock"></i> ${esc(item.lastDate)}</span>` : ''}
        </div>
        <div class="tsj-rc-meta-row">
          <span class="tsj-section-badge"><i class="fa-solid fa-layer-group"></i> ${esc(sectionLabel)}</span>
          ${relTime ? `<span class="tsj-updated-time"><i class="fa-regular fa-clock"></i> ${esc(relTime)} अपडेट</span>` : ''}
        </div>
        <a class="tsj-rc-apply" href="${esc(slug)}"><i class="fa-solid fa-arrow-right"></i> View / Apply</a>
      </div>`;
  }

  /* ── TRENDING TAGS HTML ─────────────────────────────────── */
  function buildTrendingHtml() {
    return `
      <div class="tsj-trending" id="tsjTrending">
        <span class="tsj-tr-label"><i class="fa-solid fa-fire"></i> Trending:</span>
        <div class="tsj-tr-tags">
          ${TRENDING.map(t => `
            <button class="tsj-tr-tag" type="button" data-q="${esc(t.q)}">
              <i class="fa-solid ${esc(t.icon)}"></i> ${esc(t.label)}
            </button>`).join('')}
        </div>
      </div>`;
  }

  /* ── RECENT SEARCHES HTML ───────────────────────────────── */
  function buildRecentHtml() {
    const recent = getRecent();
    if (!recent.length) return '';
    return `
      <div class="tsj-recent">
        <div class="tsj-recent-hd">
          <span><i class="fa-solid fa-clock-rotate-left"></i> Recent Searches</span>
          <button type="button" id="tsjClearRecent" class="tsj-clear-btn">Clear</button>
        </div>
        <div class="tsj-recent-tags">
          ${recent.map(r => `<button class="tsj-recent-tag" type="button" data-q="${esc(r)}">${esc(r)}</button>`).join('')}
        </div>
      </div>`;
  }

  /* ── FILTERS HTML ───────────────────────────────────────── */
  function buildFiltersHtml() {
    const quals  = ['8th Pass', '10th Pass', '12th Pass', 'ITI', 'Diploma', 'Graduation', 'Post Graduation', 'B.Tech'];
    const states = ['All India', 'Haryana', 'Uttar Pradesh', 'Bihar', 'Rajasthan', 'Madhya Pradesh', 'Maharashtra', 'Punjab', 'Delhi'];
    const cats   = ['SSC', 'Railway', 'Bank', 'Police', 'Defence', 'Teaching', 'State Jobs', 'UPSC', 'Medical', 'ITI Jobs', 'PSU'];

    return `
      <div class="tsj-filters" id="tsjFilters">
        <div class="tsj-filter-row">
          <select class="tsj-filter-sel" id="fQual" aria-label="Filter by Qualification">
            <option value="">📚 All Qualifications</option>
            ${quals.map(q => `<option value="${esc(q)}">${esc(q)}</option>`).join('')}
          </select>
          <select class="tsj-filter-sel" id="fState" aria-label="Filter by State">
            <option value="">📍 All States</option>
            ${states.map(s => `<option value="${esc(s)}">${esc(s)}</option>`).join('')}
          </select>
          <select class="tsj-filter-sel" id="fCat" aria-label="Filter by Category">
            <option value="">🏷️ All Categories</option>
            ${cats.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('')}
          </select>
          <button type="button" class="tsj-filter-clear" id="tsjFilterClear">Reset</button>
        </div>
      </div>`;
  }

  /* ── INJECT CSS ─────────────────────────────────────────── */
  function injectStyles() {
    if (document.getElementById('tsj-search-styles')) return;
    const style = document.createElement('style');
    style.id = 'tsj-search-styles';
    style.textContent = `
      /* ── Search Wrapper ── */
      .tsj-search-wrap { position: relative; }

      /* ── Dropdown ── */
      #tsjDrop {
        background: #fff; border: 1px solid #e2e8f0;
        border-radius: 14px; box-shadow: 0 16px 48px rgba(13,34,87,.18);
        z-index: 99999; max-height: 420px; overflow-y: auto;
        display: none; animation: tsjFadeIn .15s ease;
      }
      #tsjDrop.open { display: block; }
      @keyframes tsjFadeIn { from { opacity:0; transform: translateY(-6px); } to { opacity:1; transform: translateY(0); } }

      /* ── Suggest items ── */
      .tsj-suggest-item {
        display: flex; align-items: center; gap: 10px;
        padding: 11px 14px; text-decoration: none; color: #0f172a;
        border-bottom: 1px solid #f8fafc; transition: background .1s; cursor: pointer;
      }
      .tsj-suggest-item:last-child { border-bottom: none; }
      .tsj-suggest-item:hover, .tsj-suggest-item.tsj-active { background: #eff6ff; }
      .tsj-si-icon { width: 30px; height: 30px; border-radius: 8px; background: #eff6ff; color: #1a56db; display: flex; align-items: center; justify-content: center; font-size: .8rem; flex-shrink: 0; }
      .tsj-si-body { flex: 1; overflow: hidden; }
      .tsj-si-title { display: block; font-size: .84rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .tsj-si-meta { display: block; font-size: .7rem; color: #64748b; margin-top: 1px; }
      .tsj-si-arr { color: #cbd5e1; font-size: .75rem; }
      .tsj-suggest-item:hover .tsj-si-arr, .tsj-suggest-item.tsj-active .tsj-si-arr { color: #1a56db; }

      /* ── Highlight ── */
      mark.srch-hl { background: #fef08a; color: #92400e; border-radius: 2px; padding: 0 1px; font-style: normal; }

      /* ── Trending ── */
      .tsj-trending { padding: 10px 14px 6px; border-bottom: 1px solid #f1f5f9; }
      .tsj-tr-label { font-size: .72rem; font-weight: 800; color: #f97316; display: block; margin-bottom: 7px; }
      .tsj-tr-tags { display: flex; flex-wrap: wrap; gap: 6px; }
      .tsj-tr-tag {
        background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa;
        border-radius: 20px; padding: 4px 10px; font-size: .7rem; font-weight: 700;
        cursor: pointer; transition: all .12s; font-family: inherit;
        display: flex; align-items: center; gap: 4px;
      }
      .tsj-tr-tag:hover { background: #f97316; color: #fff; border-color: #f97316; }

      /* ── Recent ── */
      .tsj-recent { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; }
      .tsj-recent-hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: 7px; font-size: .72rem; font-weight: 800; color: #475569; }
      .tsj-clear-btn { background: none; border: 1px solid #e2e8f0; border-radius: 6px; padding: 2px 8px; font-size: .68rem; color: #94a3b8; cursor: pointer; font-family: inherit; }
      .tsj-clear-btn:hover { color: #ef4444; border-color: #ef4444; }
      .tsj-recent-tags { display: flex; flex-wrap: wrap; gap: 5px; }
      .tsj-recent-tag {
        background: #f8fafc; color: #475569; border: 1px solid #e2e8f0;
        border-radius: 6px; padding: 4px 10px; font-size: .72rem; font-weight: 600;
        cursor: pointer; font-family: inherit; transition: all .12s;
      }
      .tsj-recent-tag:hover { background: #eff6ff; color: #1a56db; border-color: #bfdbfe; }

      /* ── Suggest more link ── */
      .tsj-suggest-more {
        display: flex; align-items: center; justify-content: center; gap: 6px;
        padding: 10px 14px; font-size: .78rem; font-weight: 700; color: #1a56db;
        text-decoration: none; border-top: 1px solid #f1f5f9; transition: background .12s;
      }
      .tsj-suggest-more:hover { background: #f0f9ff; }

      /* ── Suggest no results ── */
      .tsj-no-suggest { padding: 14px; font-size: .82rem; color: #94a3b8; text-align: center; }

      /* ── Full results panel ── */
      #tsjResultsPanel { margin-top: 12px; display: none; }
      #tsjResultsPanel.open { display: block; }

      /* ── Filters ── */
      .tsj-filters { margin-bottom: 10px; }
      .tsj-filter-row { display: flex; flex-wrap: wrap; gap: 6px; }
      .tsj-filter-sel {
        flex: 1; min-width: 130px; padding: 7px 10px; border: 1.5px solid #e2e8f0;
        border-radius: 8px; font-size: .78rem; font-weight: 600; color: #334155;
        background: #fff; font-family: inherit; cursor: pointer; outline: none;
        transition: border-color .15s;
      }
      .tsj-filter-sel:focus { border-color: #1a56db; }
      .tsj-filter-clear {
        padding: 7px 12px; background: #f1f5f9; border: 1.5px solid #e2e8f0;
        border-radius: 8px; font-size: .75rem; font-weight: 700; color: #64748b;
        cursor: pointer; font-family: inherit; transition: all .12s;
      }
      .tsj-filter-clear:hover { background: #ef4444; color: #fff; border-color: #ef4444; }

      /* ── Result cards ── */
      .tsj-results-grid { display: flex; flex-direction: column; gap: 8px; }
      .tsj-result-card {
        background: rgba(255,255,255,.92); border: 1px solid rgba(255,255,255,.5);
        border-radius: 10px; padding: 12px 14px; transition: all .15s;
        backdrop-filter: blur(4px);
      }
      .tsj-result-card:hover { background: #fff; box-shadow: 0 4px 16px rgba(13,34,87,.12); transform: translateY(-1px); }
      .tsj-rc-head { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px; }
      .tsj-rc-icon { width: 36px; height: 36px; border-radius: 10px; background: #eff6ff; color: #1a56db; display: flex; align-items: center; justify-content: center; font-size: .95rem; flex-shrink: 0; }
      .tsj-rc-info { flex: 1; }
      .tsj-rc-title { font-size: .86rem; font-weight: 800; color: #1a56db; text-decoration: none; display: block; line-height: 1.3; }
      .tsj-rc-title:hover { text-decoration: underline; }
      .tsj-rc-dept { font-size: .72rem; color: #64748b; margin-top: 2px; }
      .tsj-rc-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }
      .tsj-tag { font-size: .68rem; font-weight: 700; padding: 2px 8px; border-radius: 20px; display: flex; align-items: center; gap: 3px; }
      .tsj-tag-qual { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
      .tsj-tag-state { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
      .tsj-tag-cat { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
      .tsj-tag-date { background: #fff1f2; color: #be123c; border: 1px solid #fecdd3; }
      .tsj-rc-apply {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 5px 12px; background: #1a56db; color: #fff; border-radius: 6px;
        font-size: .72rem; font-weight: 800; text-decoration: none; transition: background .12s;
      }
      .tsj-rc-apply:hover { background: #1e40af; }

      /* ── Section Source Badge + Updated Time ── */
      .tsj-rc-meta-row {
        display: flex; align-items: center; gap: 8px;
        flex-wrap: wrap; margin-bottom: 8px;
      }
      .tsj-section-badge {
        display: inline-flex; align-items: center; gap: 4px;
        font-size: .66rem; font-weight: 700; padding: 2px 8px;
        border-radius: 20px;
        background: #f0f9ff; color: #0369a1;
        border: 1px solid #bae6fd;
      }
      .tsj-updated-time {
        display: inline-flex; align-items: center; gap: 4px;
        font-size: .66rem; font-weight: 600;
        color: #6b7280;
      }

      /* ── Results header ── */
      .tsj-res-head {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 10px; flex-wrap: wrap; gap: 6px;
      }
      .tsj-res-count { font-size: .8rem; color: rgba(255,255,255,.85); font-weight: 700; }
      .tsj-res-close {
        background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.3);
        border-radius: 7px; padding: 4px 10px; font-size: .72rem; font-weight: 700;
        color: #fff; cursor: pointer; font-family: inherit;
      }
      .tsj-res-close:hover { background: rgba(255,255,255,.25); }

      /* ── View all results link ── */
      .tsj-view-all-results {
        display: flex; align-items: center; justify-content: center; gap: 6px;
        margin-top: 10px; padding: 10px; background: rgba(255,255,255,.15);
        border: 1.5px solid rgba(255,255,255,.25); border-radius: 9px;
        color: #fff; font-size: .8rem; font-weight: 800; text-decoration: none;
        transition: background .15s;
      }
      .tsj-view-all-results:hover { background: rgba(255,255,255,.25); }

      /* ── Trending in hero (outside dropdown) ── */
      .hero-trending-row {
        display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px;
      }
      .hero-tr-tag {
        background: rgba(255,255,255,.12); color: rgba(255,255,255,.92);
        border: 1px solid rgba(255,255,255,.25); border-radius: 20px;
        padding: 5px 12px; font-size: .72rem; font-weight: 700;
        cursor: pointer; font-family: inherit; transition: all .15s;
        display: inline-flex; align-items: center; gap: 5px;
      }
      .hero-tr-tag:hover { background: rgba(255,255,255,.25); color: #fff; }

      @media (max-width: 480px) {
        #tsjDrop { border-radius: 10px; max-height: 400px; }
        .tsj-filter-sel { min-width: 100%; }
        .tsj-result-card { padding: 10px 11px; }
      }
    `;
    document.head.appendChild(style);
  }

  /* ── HERO SEARCH SETUP ──────────────────────────────────── */
  function setupHeroSearch() {
    const input = document.getElementById('heroSearch');
    const btn   = document.getElementById('heroSearchBtn');
    if (!input || !btn) return;

    // Wrap input+button in relative div if needed
    const parent = input.closest('.hero-search-box');
    if (parent && !parent.closest('.tsj-search-wrap')) {
      const wrapper = parent.parentElement;
      if (wrapper) wrapper.classList.add('tsj-search-wrap');
    }

    injectStyles();

    // Remove old suggest div if present
    const oldSuggest = document.getElementById('searchSuggest') || document.getElementById('heroSearchSuggestResults');
    if (oldSuggest) oldSuggest.remove();

    // Create dropdown — appended to body with fixed positioning so it's never clipped
    const drop = document.createElement('div');
    drop.id = 'tsjDrop';
    drop.setAttribute('role', 'listbox');
    drop.setAttribute('aria-label', 'Search suggestions');
    document.body.appendChild(drop);

    // Position dropdown below the search input using getBoundingClientRect
    function positionDrop() {
      const rect = (input.closest('.hero-search-box') || input).getBoundingClientRect();
      drop.style.position = 'fixed';
      drop.style.top  = (rect.bottom + 6) + 'px';
      drop.style.left = rect.left + 'px';
      drop.style.width = rect.width + 'px';
      drop.style.maxHeight = '420px';
      drop.style.zIndex = '99999';
    }
    positionDrop();
    window.addEventListener('resize',  () => { if (drop.classList.contains('open')) positionDrop(); });
    window.addEventListener('scroll',  () => { if (drop.classList.contains('open')) positionDrop(); }, true);

    const searchBoxParent = input.parentElement;

    // Replace old results panel
    const oldPanel = document.getElementById('heroSearchResults');
    const resultsPanel = document.createElement('div');
    resultsPanel.id = 'tsjResultsPanel';
    if (oldPanel) {
      oldPanel.replaceWith(resultsPanel);
    } else {
      searchBoxParent.after(resultsPanel);
    }

    // Inject hero trending tags
    const heroInner = input.closest('.hero-inner');
    if (heroInner && !heroInner.querySelector('.hero-trending-row')) {
      const trendRow = document.createElement('div');
      trendRow.className = 'hero-trending-row';
      trendRow.setAttribute('aria-label', 'Trending searches');
      trendRow.innerHTML = `<span style="color:rgba(255,255,255,.6);font-size:.68rem;font-weight:700;align-self:center;">🔥 Trending:</span>` +
        TRENDING.slice(0, 6).map(t => `<button class="hero-tr-tag" type="button" data-q="${esc(t.q)}"><i class="fa-solid ${esc(t.icon)}"></i> ${esc(t.label)}</button>`).join('');
      searchBoxParent.after(trendRow);
      trendRow.querySelectorAll('.hero-tr-tag').forEach(b => {
        b.addEventListener('click', () => { input.value = b.dataset.q; input.focus(); triggerSearch(b.dataset.q, true); });
      });
    }

    /* ── Dropdown content ── */
    function showDefaultDrop() {
      positionDrop();
      const recentHtml = buildRecentHtml();
      const trendingHtml = buildTrendingHtml();
      drop.innerHTML = (recentHtml || trendingHtml)
        ? `${recentHtml}${trendingHtml}`
        : `<div class="tsj-no-suggest">Type to search jobs, admit cards, results…</div>`;
      drop.classList.add('open');
      wireDropEvents();
    }

    function showSuggest(q) {
      positionDrop();

      // ✅ FIX: JSON load hone ka wait mat karo — SEED_DATA se search karo abhi,
      //         aur agar JSON load ho jaye to auto-refresh karo
      const results = doSearch(q, {}).slice(0, CFG.maxSuggest);
      if (!results.length) {
        drop.innerHTML = `<div class="tsj-no-suggest">No results for "<strong>${esc(q)}</strong>". Try: SSC, Railway, Bank, Police…</div>`;
      } else {
        activeIndex = -1;
        suggestItems = results;
        drop.innerHTML =
          results.map((r, i) => renderSuggestItem(r, q, i)).join('') +
          `<a class="tsj-suggest-more" href="${CFG.searchPageUrl}?q=${encodeURIComponent(q)}">
            <i class="fa-solid fa-magnifying-glass"></i> View all results for "${esc(q)}"
          </a>`;
      }
      drop.classList.add('open');
      wireDropEvents();

      // ✅ FIX: Agar JSON abhi load ho raha hai to 500ms baad re-render karo (updated data se)
      if (!jsonIndexReady) {
        const currentQ = q;
        setTimeout(() => {
          if (input.value.trim().toLowerCase() === currentQ.trim().toLowerCase() && jsonIndexReady) {
            showSuggest(currentQ);
          }
        }, 800);
      }
    }

    function wireDropEvents() {
      drop.querySelectorAll('.tsj-tr-tag').forEach(b => {
        b.addEventListener('click', () => { input.value = b.dataset.q; triggerSearch(b.dataset.q, true); });
      });
      drop.querySelectorAll('.tsj-recent-tag').forEach(b => {
        b.addEventListener('click', () => { input.value = b.dataset.q; triggerSearch(b.dataset.q, true); });
      });
      const clearBtn = drop.querySelector('#tsjClearRecent');
      if (clearBtn) {
        clearBtn.addEventListener('click', () => {
          try { localStorage.removeItem(CFG.recentKey); } catch {}
          showDefaultDrop();
        });
      }
    }

    function triggerSearch(q, fromTag = false) {
      drop.classList.remove('open');
      if (!q.trim()) return;
      saveRecent(q);
      showFullResults(q);
    }

    function showFullResults(q) {
      resultsPanel.classList.add('open');

      // ✅ FIX: seedha search karo, JSON load ka wait nahi — SEED_DATA available hai
      const results = doSearch(q, currentFilters);

      if (!results.length) {
        resultsPanel.innerHTML = `
          <div class="tsj-res-head">
            <span class="tsj-res-count">No results for "${esc(q)}"</span>
            <button type="button" class="tsj-res-close" id="tsjResClose">✕ Close</button>
          </div>
          <div class="tsj-result-card" style="text-align:center;color:rgba(255,255,255,.75);padding:20px;">
            <p>Try: SSC, Railway, Bank, Police, Haryana, Army, 10th, 12th, ITI…</p>
          </div>`;
      } else {
        resultsPanel.innerHTML = `
          <div class="tsj-res-head">
            <span class="tsj-res-count"><i class="fa-solid fa-magnifying-glass"></i> ${results.length} result(s) for "${esc(q)}"</span>
            <button type="button" class="tsj-res-close" id="tsjResClose">✕ Close</button>
          </div>
          ${buildFiltersHtml()}
          <div class="tsj-results-grid" id="tsjGrid">
            ${results.slice(0, CFG.maxResults).map(r => renderResultCard(r, q)).join('')}
          </div>
          ${results.length > CFG.maxResults ? `<a class="tsj-view-all-results" href="${CFG.searchPageUrl}?q=${encodeURIComponent(q)}"><i class="fa-solid fa-list"></i> View all ${results.length} results</a>` : ''}`;

        // Bind filter changes
        const fQual  = resultsPanel.querySelector('#fQual');
        const fState = resultsPanel.querySelector('#fState');
        const fCat   = resultsPanel.querySelector('#fCat');
        const fReset = resultsPanel.querySelector('#tsjFilterClear');
        const grid   = resultsPanel.querySelector('#tsjGrid');

        function applyFilters() {
          currentFilters.qual  = fQual ? fQual.value : '';
          currentFilters.state = fState ? fState.value : '';
          currentFilters.cat   = fCat ? fCat.value : '';
          const filtered = doSearch(q, currentFilters);
          if (grid) grid.innerHTML = filtered.slice(0, CFG.maxResults).map(r => renderResultCard(r, q)).join('') ||
            `<div style="color:rgba(255,255,255,.7);padding:12px;font-size:.82rem;">No results match the selected filters.</div>`;
        }
        if (fQual) fQual.addEventListener('change', applyFilters);
        if (fState) fState.addEventListener('change', applyFilters);
        if (fCat) fCat.addEventListener('change', applyFilters);
        if (fReset) fReset.addEventListener('click', () => {
          currentFilters = { qual: '', state: '', cat: '', sort: 'latest' };
          if (fQual) fQual.value = '';
          if (fState) fState.value = '';
          if (fCat) fCat.value = '';
          applyFilters();
        });
      }

      resultsPanel.querySelector('#tsjResClose')?.addEventListener('click', () => {
        resultsPanel.classList.remove('open');
        resultsPanel.innerHTML = '';
        input.value = '';
        input.focus();
      });
    }

    /* ── Events ── */
    const debouncedSuggest = debounce(q => {
      if (q.trim().length < 1) { showDefaultDrop(); return; }  // ✅ 1 char se suggest shuru
      showSuggest(q);
    }, CFG.debounceMs);

    input.addEventListener('input', function () { debouncedSuggest(this.value); });
    input.addEventListener('focus', function () {
      if (this.value.trim().length >= 1) showSuggest(this.value);  // ✅ 1 char se
      else showDefaultDrop();
    });

    // Keyboard navigation
    input.addEventListener('keydown', function (e) {
      const items = drop.querySelectorAll('.tsj-suggest-item');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIndex = Math.min(activeIndex + 1, items.length - 1);
        items.forEach((el, i) => el.classList.toggle('tsj-active', i === activeIndex));
        if (items[activeIndex]) items[activeIndex].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, -1);
        items.forEach((el, i) => el.classList.toggle('tsj-active', i === activeIndex));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (activeIndex >= 0 && items[activeIndex]) {
          items[activeIndex].click();
        } else {
          triggerSearch(input.value);
        }
        drop.classList.remove('open');
      } else if (e.key === 'Escape') {
        drop.classList.remove('open');
        activeIndex = -1;
      }
    });

    btn.addEventListener('click', () => { triggerSearch(input.value); drop.classList.remove('open'); });

    // Touch on suggestions
    drop.addEventListener('click', function (e) {
      const item = e.target.closest('.tsj-suggest-item');
      if (item) saveRecent(input.value);
    });

    document.addEventListener('click', function (e) {
      if (!drop.contains(e.target) && e.target !== input && e.target !== btn) drop.classList.remove('open');
    });

    // Mobile search btn
    const mobileBtn = document.getElementById('mobileSearchBtn');
    if (mobileBtn) {
      mobileBtn.addEventListener('click', () => {
        const hero = document.getElementById('hero-search-section');
        if (hero) { hero.scrollIntoView({ behavior: 'smooth', block: 'start' }); setTimeout(() => input.focus(), 400); }
      });
    }
  }

  /* ── HEADER SEARCH SETUP ────────────────────────────────── */
  function setupHeaderSearch() {
    const hInput = document.getElementById('headerSearch');
    const hBtn   = document.getElementById('headerSearchBtn');
    if (hInput && hBtn) {
      hBtn.addEventListener('click', () => {
        if (hInput.value.trim()) window.location.href = `${CFG.searchPageUrl}?q=${encodeURIComponent(hInput.value.trim())}`;
      });
      hInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && hInput.value.trim()) window.location.href = `${CFG.searchPageUrl}?q=${encodeURIComponent(hInput.value.trim())}`;
      });
    }

    // openSearchBtn (mobile)
    const openBtn = document.getElementById('openSearchBtn');
    if (openBtn) {
      openBtn.addEventListener('click', () => {
        const heroInput = document.getElementById('heroSearch');
        if (heroInput) {
          const hero = document.getElementById('hero-search-section');
          if (hero) hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
          setTimeout(() => heroInput.focus(), 350);
        }
      });
    }
  }

  /* ── SEARCH.HTML PAGE HANDLER ───────────────────────────── */
  function setupSearchPage() {
    const container = document.getElementById('searchPageResults');
    if (!container) return;

    const params = new URLSearchParams(location.search);
    const q = params.get('q') || '';

    // Update page title + meta
    if (q) {
      document.title = `${q} – Jobs Search | Top Sarkari Jobs 2026`;
      const meta = document.querySelector('meta[name="description"]');
      if (meta) meta.content = `Search results for "${q}" – Find government jobs, results, admit cards on Top Sarkari Jobs.`;
    }

    // Sync input if present
    const pageInput = document.getElementById('searchPageInput');
    if (pageInput && q) pageInput.value = q;

    function renderPage(query) {
      const results = doSearch(query, currentFilters);
      container.innerHTML = results.length
        ? `<p class="sp-count">${results.length} result(s) for "<strong>${esc(query)}</strong>"</p>
           ${buildFiltersHtml()}
           <div class="tsj-results-grid sp-grid" id="tsjGrid">
             ${results.slice(0, 60).map(r => renderResultCard(r, query)).join('')}
           </div>`
        : `<p class="sp-count">No results found for "<strong>${esc(query)}</strong>". Try: SSC, Railway, Bank, Police, Haryana…</p>`;

      const fQual  = container.querySelector('#fQual');
      const fState = container.querySelector('#fState');
      const fCat   = container.querySelector('#fCat');
      const fReset = container.querySelector('#tsjFilterClear');
      const grid   = container.querySelector('#tsjGrid');

      function applyFilters() {
        currentFilters.qual  = fQual ? fQual.value : '';
        currentFilters.state = fState ? fState.value : '';
        currentFilters.cat   = fCat ? fCat.value : '';
        if (grid) grid.innerHTML = doSearch(query, currentFilters).slice(0, 60).map(r => renderResultCard(r, query)).join('');
      }
      if (fQual) fQual.addEventListener('change', applyFilters);
      if (fState) fState.addEventListener('change', applyFilters);
      if (fCat) fCat.addEventListener('change', applyFilters);
      if (fReset) fReset.addEventListener('click', () => {
        currentFilters = { qual: '', state: '', cat: '', sort: 'latest' };
        if (fQual) fQual.value = '';
        if (fState) fState.value = '';
        if (fCat) fCat.value = '';
        applyFilters();
      });

      if (pageInput) {
        pageInput.addEventListener('keydown', e => {
          if (e.key === 'Enter' && pageInput.value.trim()) {
            const newQ = pageInput.value.trim();
            history.replaceState(null, '', `${CFG.searchPageUrl}?q=${encodeURIComponent(newQ)}`);
            saveRecent(newQ);
            renderPage(newQ);
          }
        });
      }
    }

    if (q) {
      saveRecent(q);
      setTimeout(() => renderPage(q), 100); // wait for JSON load
    }

    container.insertAdjacentHTML('beforebegin', `
      <style>
        .sp-count { font-size:.88rem; color:#475569; font-weight:700; margin-bottom:12px; }
        .sp-grid { display:flex; flex-direction:column; gap:8px; }
        .tsj-result-card { background:#fff; border:1px solid #e2e8f0; }
        .tsj-result-card:hover { box-shadow:0 4px 16px rgba(13,34,87,.1); }
        .tsj-rc-title { color:#1a56db; }
        .tsj-res-count { color:#334155; }
      </style>`);
  }

  /* ── DOM SCRAPER — page ke rendered cards se data nikalo ────────
   *  script.js jo section-cards DOM mein render karta hai (dailyupdates.json,
   *  Complete_Jobs_Full_Data.json etc.) unka data seedha allData mein dalo.
   *  Yeh function JSON load fail hone par bhi kaam karta hai.
   * ────────────────────────────────────────────────────────────── */
  function scrapeDomCards() {
    const seen = new Set(allData.map(d => d.slug));
    let count = 0;

    // All .section-link anchors (rendered by script.js section cards)
    const anchors = Array.from(document.querySelectorAll(
      '.section-link[href], .section-list a[href], #dynamic-sections a[href], #daily-updates-sections a[href]'
    ));

    anchors.forEach(a => {
      const href = a.getAttribute('href') || '';
      if (!href || href === '#') return;

      // Get title: .t span me se (script.js ka format)
      const tSpan = a.querySelector('.t');
      let title = '';
      if (tSpan) {
        // Remove date span text to get clean title
        const dSpan = tSpan.querySelector('.d');
        if (dSpan) {
          title = tSpan.textContent.replace(dSpan.textContent, '').trim();
        } else {
          title = tSpan.textContent.trim();
        }
      } else {
        title = a.textContent.trim().split('|')[0].trim();
      }
      if (!title || title.length < 3) return;

      // Get date from .d span
      const dSpan2 = a.querySelector('.d');
      const lastDate = dSpan2 ? dSpan2.textContent.replace('|', '').trim() : '';

      // Section title from closest section-card header
      const card = a.closest('.section-card, article');
      let sectionSource = '';
      let catIcon = 'fa-briefcase';
      if (card) {
        const headSpan = card.querySelector('.section-head span');
        sectionSource = headSpan ? headSpan.textContent.trim() : '';
        const headIcon = card.querySelector('.section-head i');
        if (headIcon) {
          const cls = Array.from(headIcon.classList).find(c => c.startsWith('fa-') && c !== 'fa-solid' && c !== 'fa-regular');
          if (cls) catIcon = cls;
        }
      }

      // Determine category from sectionSource
      const src = sectionSource.toLowerCase();
      let cat = 'Latest Job';
      if (src.includes('admit')) cat = 'Admit Card';
      else if (src.includes('result')) cat = 'Result';
      else if (src.includes('answer key')) cat = 'Answer Key';
      else if (src.includes('admission')) cat = 'Admission';
      else if (src.includes('offline')) cat = 'Offline Form';
      else if (src.includes('bank')) cat = 'Bank';
      else if (src.includes('railway')) cat = 'Railway';
      else if (src.includes('police') || src.includes('defence')) cat = 'Police';
      else if (src.includes('teaching') || src.includes('faculty')) cat = 'Teaching';
      else if (src.includes('10th')) cat = 'State Jobs';
      else if (src.includes('iti')) cat = 'ITI Jobs';
      else if (src.includes('medical')) cat = 'Medical';
      else if (src.includes('last date')) cat = 'Last Date Reminder';

      const key = href;
      if (seen.has(key)) return;
      seen.add(key);

      allData.push({
        title,
        slug: href,
        dept: sectionSource,
        qual: '',
        state: 'All India',
        cat,
        tags: title + ' ' + sectionSource + ' sarkari naukri 2026',
        lastDate,
        icon: catIcon,
        lastUpdated: new Date().toISOString(),
        sectionSource,
      });
      count++;
    });

    if (count > 0) {
      console.log('[smart-search] DOM scraper added', count, 'items from rendered cards');
      // Rebuild Fuse with new data
      if (window.Fuse) buildFuse(allData);
    }
    return count;
  }

  /* ── INIT ───────────────────────────────────────────────── */
  function init() {
    injectStyles();
    loadFuse(() => buildFuse(allData));
    loadJsonFiles(); // async, updates data + rebuilds Fuse when done
    setupHeroSearch();
    setupHeaderSearch();
    setupSearchPage();

    // ✅ DOM scraper: page render hone ke baad cards ka data index mein dalo
    // script.js async render karta hai, isliye multiple attempts
    function tryDomScrape(attemptsLeft) {
      const found = scrapeDomCards();
      if (found > 0) {
        // Ek baar aur try karo — script.js baad mein aur cards add kar sakta hai
        setTimeout(() => scrapeDomCards(), 2000);
      } else if (attemptsLeft > 0) {
        setTimeout(() => tryDomScrape(attemptsLeft - 1), 800);
      }
    }
    setTimeout(() => tryDomScrape(5), 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
