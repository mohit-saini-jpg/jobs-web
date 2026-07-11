(() => {
  "use strict";

  // ✅ SEARCH INDEX: smart-search.js is array ko monitor karta hai
  // Pehle se exist kare to use karo, nahi to nayi array banao
  window.tsjSearchIndex = window.tsjSearchIndex || [];

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  const isToolsPage = location.pathname.includes("tools");

  const safe = (v) => (v ?? "").toString().trim();

  /* ── Smart Date Badge: Universal parser for ALL JSON date formats ──
     "2026-06-02" | "02-06-2026" | "2 Jun 2026" | "From 27/05/2026"
  ── */
  function formatDateBadge(raw) {
    if (!raw || typeof raw !== 'string') return null;
    raw = raw.trim();
    if (!raw) return null;
    const hasFrom = /^From\s+/i.test(raw);
    if (hasFrom) raw = raw.replace(/^From\s+/i, '');
    if (/please refer|days from|date of pub|see notif|check off/i.test(raw))
      return { display: 'Check Notification', colorClass: 'd-grey' };
    if (/walk.?in|walkin/i.test(raw))
      return { display: 'Walk-in', colorClass: 'd-grey' };
    const MO = {jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12};
    let d=0,mo=0,yr=0,m;
    m=raw.match(/^(\d{4})-(\d{2})-(\d{2})/); if(m){yr=+m[1];mo=+m[2];d=+m[3];}
    if(!yr){m=raw.match(/^(\d{1,2})[\-\/](\d{1,2})[\-\/](\d{4})/);if(m){d=+m[1];mo=+m[2];yr=+m[3];}}
    if(!yr){m=raw.match(/(\d{1,2})\s+([A-Za-z]{3})\.?\s+(\d{4})/);if(m){const x=MO[m[2].slice(0,3).toLowerCase()];if(x){d=+m[1];mo=x;yr=+m[3];}}}
    if(!yr){m=raw.match(/([A-Za-z]{3})\s+(\d{1,2})[,.]?\s+(\d{4})/);if(m){const x=MO[m[1].slice(0,3).toLowerCase()];if(x){mo=x;d=+m[2];yr=+m[3];}}}
    if(!yr||!mo||!d) return {display:(hasFrom?'From ':'')+raw.slice(0,18),colorClass:'d-grey'};
    const display=(hasFrom?'From ':'')+String(d).padStart(2,'0')+'/'+String(mo).padStart(2,'0')+'/'+yr;
    const today=new Date();today.setHours(0,0,0,0);
    const diff=Math.ceil((new Date(yr,mo-1,d)-today)/86400000);
    return {display,colorClass:diff<0?'d-expired':diff<=3?'d-red':diff<=7?'d-orange':'d-green'};
  }

  // Safely handles internal absolute URLs
  function normalizeUrl(raw) {
    const s = safe(raw);
    if (!s) return "";
    if (/^(https?:)?\/\//i.test(s) || /^(mailto:|tel:)/i.test(s)) return s;
    if (s.startsWith("#") || s.startsWith("?")) return s;
    if (s.startsWith("/") || s.includes(".html") || s.startsWith("./") || s.startsWith("../")) return s;
    return "https://" + s.replace(/^\/+/, "");
  }


  /* ─── Convert Complete_Jobs_Full_Data.json → sections format ─── */
  const JOBS_CAT_META = {
    "Latest_Notifications": { id: "Latest Notifications",    title: "Latest Notifications",  color: "linear-gradient(135deg,#dc2626,#b91c1c)", icon: "fa-solid fa-bell" },
    "10TH_Pass":            { id: "10th Pass jobs",           title: "10th Pass Jobs",         color: "linear-gradient(135deg,#0284c7,#0369a1)", icon: "fa-solid fa-graduation-cap" },
    "8TH_Pass":             { id: "8th Pass",                 title: "8th Pass Jobs",          color: "linear-gradient(135deg,#7c3aed,#6d28d9)", icon: "fa-solid fa-book" },
    "12TH_Pass":            { id: "12th Pass jobs",           title: "12th Pass Jobs",         color: "linear-gradient(135deg,#059669,#047857)", icon: "fa-solid fa-graduation-cap" },
    "Diploma":              { id: "Diploma Jobs",             title: "Diploma Jobs",           color: "linear-gradient(135deg,#d97706,#b45309)", icon: "fa-solid fa-scroll" },
    "ITI":                  { id: "ITI Jobs",                 title: "ITI Jobs",               color: "linear-gradient(135deg,#0891b2,#0e7490)", icon: "fa-solid fa-wrench" },
    "B_Tech_BE":            { id: "B.Tech Jobs",              title: "B.Tech / B.E. Jobs",     color: "linear-gradient(135deg,#4f46e5,#4338ca)", icon: "fa-solid fa-microchip" },
    "B_Com":                { id: "B.Com Jobs",               title: "B.Com Jobs",             color: "linear-gradient(135deg,#0d9488,#0f766e)", icon: "fa-solid fa-chart-line" },
    "Any_Graduate":         { id: "Graduation jobs",          title: "Any Graduate Jobs",      color: "linear-gradient(135deg,#2563eb,#1d4ed8)", icon: "fa-solid fa-graduation-cap" },
    "Any_Post_Graduate":    { id: "Post Graduation jobs",     title: "Post Graduate Jobs",     color: "linear-gradient(135deg,#9333ea,#7e22ce)", icon: "fa-solid fa-user-tie" },
    "Railway_Jobs":         { id: "Railway Jobs",             title: "Railway Jobs",           color: "linear-gradient(135deg,#b45309,#92400e)", icon: "fa-solid fa-train" },
    "Police_Defence":       { id: "Police Jobs",              title: "Police / Defence Jobs",  color: "linear-gradient(135deg,#1e40af,#1e3a8a)", icon: "fa-solid fa-shield-halved" },
    "Teaching_Faculty":     { id: "Teacher Jobs",             title: "Teaching / Faculty Jobs",color: "linear-gradient(135deg,#16a34a,#15803d)", icon: "fa-solid fa-chalkboard-user" },
    "Bank_Jobs":            { id: "Bank Jobs",                title: "Bank Jobs",              color: "linear-gradient(135deg,#ca8a04,#a16207)", icon: "fa-solid fa-building-columns" },
    "Medical_Hospital":     { id: "Medical Jobs",             title: "Medical / Hospital Jobs",color: "linear-gradient(135deg,#dc2626,#b91c1c)", icon: "fa-solid fa-stethoscope" },
    "Last_Date_Reminder":   { id: "Last Date Reminder",       title: "Last Date Reminder",     color: "linear-gradient(135deg,#e11d48,#be123c)", icon: "fa-solid fa-clock" },
    "SR_Latest_Jobs":       { id: "SR Latest Jobs",           title: "Latest Jobs",    color: "linear-gradient(135deg,#0369a1,#0284c7)", icon: "fa-solid fa-file-pen" },
    "SR_Result":            { id: "SR Result",                title: "Result",         color: "linear-gradient(135deg,#047857,#059669)", icon: "fa-solid fa-trophy" },
    "SR_Admit_Card":        { id: "SR Admit Card",            title: "Admit Card",        color: "linear-gradient(135deg,#6d28d9,#7c3aed)", icon: "fa-solid fa-id-card" },
    "SR_Admission":         { id: "SR Admission",             title: "Admission",         color: "linear-gradient(135deg,#0e7490,#0891b2)", icon: "fa-solid fa-graduation-cap" },
    "SR_Answer_Key":        { id: "SR Answer Key",            title: "Answer Key",        color: "linear-gradient(135deg,#b45309,#d97706)", icon: "fa-solid fa-key" },
    "UPCOMING_JOBS":        { id: "Upcoming Jobs",            title: "Upcoming Jobs",          color: "linear-gradient(135deg,#15803d,#16a34a)", icon: "fa-solid fa-calendar-plus" },
    "STATE_JOBS":           { id: "State Jobs",               title: "State Jobs",        color: "linear-gradient(135deg,#9333ea,#a855f7)", icon: "fa-solid fa-map-location-dot", viewMoreUrl: "/state-jobs/" },
    "CENTRAL_JOBS":         { id: "Central Jobs",             title: "Central Jobs",      color: "linear-gradient(135deg,#0f766e,#0d9488)", icon: "fa-solid fa-landmark" },
    "ADMISSIONS":           { id: "Admissions",               title: "Admissions",        color: "linear-gradient(135deg,#be123c,#e11d48)", icon: "fa-solid fa-school" },
    "LATEST_JOBS NEW":      { id: "Latest Jobs New",          title: "Latest Jobs New",        color: "linear-gradient(135deg,#dc2626,#b91c1c)", icon: "fa-solid fa-fire" },
    "OFFLINE_FORM":         { id: "Offline Form",             title: "Offline Form",      color: "linear-gradient(135deg,#475569,#334155)", icon: "fa-solid fa-file-pen" },
  };

  /* Slugify a job title the same way the Python generator does */
  function slugifyForJob(title) {
    return title
      .normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
      .replace(/&/g, " and ").replace(/['']/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-")
      .slice(0, 120) || "official-link";
  }

  /* ── jobMatchesCategory: supports both `categories` array and legacy `category` string ── */
  function jobMatchesCategory(job, catKey) {
    if (Array.isArray(job.categories)) {
      return job.categories.includes(catKey);
    }
    return (job.category || job.sr_category || job.cat || '').trim() === catKey;
  }

  /*
   * ══════════════════════════════════════════════════════════════════════
   *  convertJobsDataToSections — MULTI-FORMAT FIX
   *
   *  Complete_Jobs_Full_Data.json ke teen possible structures handle karta hai:
   *
   *  Format A (Expected):
   *    { "Railway_Jobs": [{basic_details:{job_title}, important_dates:{...}}], ... }
   *
   *  Format B (Flat jobs array with category field):
   *    { "jobs": [{ "title": "...", "category": "Railway_Jobs", ... }] }
   *
   *  Format C (Alternative key names — title at root, different date keys):
   *    { "Railway_Jobs": [{ "title": "...", "last_date": "...", "slug": "..." }] }
   *
   *  Aur cross-key aliases bhi handle karta hai, jaise:
   *    "railway_jobs" → "Railway_Jobs", "RAILWAY_JOBS" → "Railway_Jobs"
   * ══════════════════════════════════════════════════════════════════════
   */
  function convertJobsDataToSections(rawData) {
    if (!rawData || typeof rawData !== "object" || Array.isArray(rawData)) return { sections: [] };

    /* ── Format B: flat jobs[] array with category field ── */
    if (Array.isArray(rawData.jobs) && rawData.jobs.length > 0) {
      /* Group flat jobs into per-category buckets using jobMatchesCategory */
      const buckets = {};
      // Collect all known catKeys from JOBS_CAT_META
      const allCatKeys = Object.keys(JOBS_CAT_META);
      rawData.jobs.forEach(job => {
        // For merged format (categories array), add to every matching bucket
        if (Array.isArray(job.categories)) {
          job.categories.forEach(cat => {
            if (!JOBS_CAT_META[cat]) return;
            if (!buckets[cat]) buckets[cat] = [];
            buckets[cat].push(job);
          });
        } else {
          const cat = (job.category || job.sr_category || job.cat || '').trim();
          if (!cat) return;
          if (!buckets[cat]) buckets[cat] = [];
          buckets[cat].push(job);
        }
      });
      rawData = buckets;
    }

    /* ── NEW FORMAT: Complete_Jobs_Full_Data.json has freejobalert_categories key ── */
    if (rawData.freejobalert_categories && typeof rawData.freejobalert_categories === 'object') {
      rawData = rawData.freejobalert_categories;
    }

    /* ── Build a normalised key lookup (case-insensitive + underscore-flexible) ── */
    /* e.g. rawData may have "railway_jobs" but JOBS_CAT_META has "Railway_Jobs" */
    const rawKeys = Object.keys(rawData);
    function findRawKey(catKey) {
      /* Exact match first */
      if (rawData[catKey] !== undefined) return catKey;
      /* Case-insensitive match */
      const lower = catKey.toLowerCase();
      for (const k of rawKeys) {
        if (k.toLowerCase() === lower) return k;
      }
      return null;
    }

    const sections = [];
    // ── JSON insertion order preserve — rawData ke keys se iterate karo ──
    for (const rawKey of Object.keys(rawData)) {
      // Find matching JOBS_CAT_META entry
      const catKey = Object.keys(JOBS_CAT_META).find(k =>
        k === rawKey || k.toLowerCase() === rawKey.toLowerCase()
      );
      if (!catKey) continue;
      const meta = JOBS_CAT_META[catKey];
      if (!meta) continue;
      const resolvedKey = rawKey;
      const jobs = rawData[resolvedKey];
      if (!Array.isArray(jobs) || !jobs.length) continue;

      const items = jobs.map(job => {
        /* ── Normalise job object across all formats ──
           Format A: job.basic_details.job_title
           Format B/C: job.title / job.name / job.post_name
        */
        const bd    = job.basic_details || {};
        const dates = job.important_dates || {};

        const name = (
          bd.job_title   ||
          bd.post_name   ||
          job.title      ||
          job.job_title  ||
          job.name       ||
          job.post_name  ||
          ""
        ).trim();
        if (!name) return null;

        /* Date: try all common field names */
        const last = (
          dates.last_date_to_apply ||
          dates.last_date          ||
          dates.last_date_apply    ||
          dates.closing_date       ||
          job.last_date_to_apply   ||
          job.last_date            ||
          job.closing_date         ||
          ""
        ).trim();

        /* Slug: use existing or generate */
        const slug = job.slug || bd.slug || slugifyForJob(name);
        const url  = "/jobs/" + slug + "/";

        return { slug, name, url, date: last || "" };
      }).filter(Boolean);

      if (!items.length) continue;
      sections.push({ id: meta.id, title: meta.title, color: meta.color, icon: meta.icon, viewMoreType: "list", items });
    }
    return { sections };
  }

  // ISSUE-002: memoize JSON fetches — downloaded once per page load only
  const __jsonCache = new Map();

  /* ── sessionStorage cache for Complete_Jobs_Full_Data.json (60 min) ──
     Avoids re-downloading 18MB JSON on every page refresh.
     PERF FIX: Do NOT pre-fetch at script load time — it competes with critical
     resources (Complete_Jobs_Full_Data.json, CSS, fonts). Load on first access only.
  ── */
  const __jobsDataPromise = (function() {
    try {
      const KEY = '__cjfd_v2', TTL = 0; // v2: always fresh — order fix
      const hit = JSON.parse(sessionStorage.getItem(KEY) || 'null');
      if (hit && (Date.now() - hit.ts) < TTL) {
        const p = Promise.resolve(hit.data);
        __jsonCache.set('Complete_Jobs_Full_Data.json', p);
        return p;
      }
    } catch(e) {}
    return null; // lazy — will fetch only when getJobsSections() is called
  })();

  /* ── PERF: Convert sections-index.json (16KB) → sections format ── */
  function convertSectionsIndex(indexData) {
    if (!indexData || typeof indexData !== 'object') return { sections: [] };
    const sections = [];
    // ── JSON insertion order preserve karo — JOBS_CAT_META order se NAHI ──
    for (const catKey of Object.keys(indexData)) {
      const items = indexData[catKey];
      if (!Array.isArray(items) || !items.length) continue;
      const meta = JOBS_CAT_META[catKey];
      if (!meta) continue; // unknown category skip
      sections.push({
        id: meta.id, title: meta.title, color: meta.color, icon: meta.icon,
        viewMoreType: 'list',
        items: items.map(item => ({
          slug: item.slug,
          name: item.name,
          url: '/jobs/' + item.slug + '/',
          date: item.date || ''
        }))
      });
    }
    return { sections };
  }

  /* ─── getJobsSections — MERGE FIX ────────────────────────────────────────
   *
   * PROBLEM: sections-index.json mein sirf 8 categories hain:
   *   Latest_Notifications, 10TH_Pass, 8TH_Pass, 12TH_Pass,
   *   Diploma, ITI, B_Tech_BE, B_Com
   *
   *   Railway_Jobs, Police_Defence, Bank_Jobs, Teaching_Faculty,
   *   Any_Graduate, Any_Post_Graduate, Medical_Hospital, Last_Date_Reminder
   *   — sections-index mein NAHI hain.
   *
   * FIX:
   *   1. sections-index.json se 8 fast categories instantly render karo
   *   2. JOBS_CAT_META ke baaki missing category keys detect karo
   *   3. Complete_Jobs_Full_Data.json se sirf unhe fetch+merge karo
   *   4. JOBS_CAT_META key order se sort karke return karo
   * ─────────────────────────────────────────────────────────────────────── */
  async function getJobsSections() {
    try {
      // Helper: fetch + cache Complete_Jobs_Full_Data.json
      async function getBigJSON() {
        if (__jobsDataPromise) {
          const raw = await __jobsDataPromise;
          if (raw) {
            __jsonCache.set('Complete_Jobs_Full_Data.json', Promise.resolve(raw));
            return raw;
          }
        }
        const raw = await getJSON('Complete_Jobs_Full_Data.json');
        if (raw) {
          try { sessionStorage.setItem('__cjfd_v1', JSON.stringify({ ts: Date.now(), data: raw })); } catch(e) {}
          __jsonCache.set('Complete_Jobs_Full_Data.json', Promise.resolve(raw));
        }
        return raw || null;
      }

      // JOBS_CAT_META mein defined order (sort key)
      const catOrder = Object.keys(JOBS_CAT_META);

      // sections-index.json available hai?
      if (window.__sectionsIndexPromise) {
        const indexData = await window.__sectionsIndexPromise;
        if (indexData) {
          const fastResult = convertSectionsIndex(indexData);

          // sections-index mein present category ids
          const coveredIds = new Set(fastResult.sections.map(s => s.id));

          // Missing categories: JOBS_CAT_META mein hain lekin sections-index mein nahi
          const missingKeys = catOrder.filter(k =>
            JOBS_CAT_META[k] && !coveredIds.has(JOBS_CAT_META[k].id)
          );

          // Always continue to merge merged_sarkari_data.json sections
          // even when Complete_Jobs categories are all covered

          // PERF FIX (permanent): the legacy 8MB Complete_Jobs_Full_Data.json
          // fetch used to run here to fill "missing" category cards. It added
          // ~8MB to the homepage (LCP ~44s, TBT ~3s on Slow-4G) for ZERO benefit —
          // sections-index.json now already carries ALL 54 homepage categories
          // (small slug/name/date items) and freejobalert_categories is empty, so
          // the big file could not fill anything anyway. The fetch is intentionally
          // removed. If a category is ever genuinely missing from the cards, FIX
          // THE INDEX BUILD (pipeline sections-index.json) — do NOT re-add the big
          // fetch here (that regresses homepage performance).
          const extraSections = [];

          // Merge: sections-index + extraSections from big JSON only
          // NOTE: SR_* categories (Latest Jobs, Result, Admit Card etc.) are already shown
          // in #sr-sections-grid by the inline script — do NOT add them here to avoid duplicates
          const allSections = [...fastResult.sections, ...extraSections];
          const seenIds = new Set();
          const deduped = allSections.filter(s => {
            if (seenIds.has(s.id)) return false;
            seenIds.add(s.id);
            return true;
          });

          // JSON insertion order preserve — sort hatayi
          return { sections: deduped };
        }
      }

      // FALLBACK: sections-index unavailable — use Complete_Jobs only

      // FALLBACK: sections-index unavailable — pure big JSON
      const raw = await getBigJSON();
      if (raw) return convertJobsDataToSections(raw);
      return { sections: [] };

    } catch (_) { return { sections: [] }; }
  }

  function getJSON(path) {
    if (__jsonCache.has(path)) return __jsonCache.get(path);
    const p = fetch(path).then((r) => {
      if (!r.ok) throw new Error("HTTP " + r.status + " for " + path);
      return r.json();
    });
    p.catch(() => __jsonCache.delete(path));
    __jsonCache.set(path, p);
    return p;
  }

  /* ── convertMergedDataToSections: merged_sarkari_data.json → sections format ──
     Categories: SR_Latest_Jobs, SR_Result, SR_Admit_Card, SR_Admission,
                 SR_Answer_Key, UPCOMING_JOBS, STATE_JOBS, CENTRAL_JOBS, ADMISSIONS
  ── */
  function convertMergedDataToSections(mergedData) {
    if (!mergedData || !Array.isArray(mergedData.jobs)) return [];
    const buckets = {};
    mergedData.jobs.forEach(job => {
      // Support both merged `categories` array and legacy `category` string
      if (Array.isArray(job.categories)) {
        job.categories.forEach(cat => {
          if (!cat || !JOBS_CAT_META[cat]) return;
          if (!buckets[cat]) buckets[cat] = [];
          buckets[cat].push(job);
        });
      } else {
        const cat = (job.category || '').trim();
        if (!cat || !JOBS_CAT_META[cat]) return;
        if (!buckets[cat]) buckets[cat] = [];
        buckets[cat].push(job);
      }
    });
    const sections = [];
    for (const [catKey, meta] of Object.entries(JOBS_CAT_META)) {
      const jobs = buckets[catKey];
      if (!jobs || !jobs.length) continue;
      const items = jobs.slice(0, 15).map(job => {
        const name = (job.title || job.post_name || '').trim().replace(/[\s\-,|]+$/, '').trim();
        if (!name) return null;
        const slug = job.slug || slugifyForJob(name);
        const url = slug ? '/jobs/' + slug + '/' : '#';
        const dates = job.important_dates || {};
        const lastDate = (dates.last_date_to_apply || dates.last_date || job.last_date || '').trim();
        const org = (job.organization || job.board_name || '').trim();
        return { slug, name, url, date: lastDate, org };
      }).filter(Boolean);
      if (!items.length) continue;
      sections.push({ id: meta.id, title: meta.title, color: meta.color, icon: meta.icon, viewMoreType: 'list', items });
    }
    return sections;
  }

  function slugifyTitle(raw) {
    const text = safe(raw)
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/&/g, " and ")
      .replace(/[’']/g, "")
      .toLowerCase();

    const slug = text
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-")
      .slice(0, 120);

    return slug || "official-link";
  }

  /** 12-char base36 fingerprint; must match redirect.html resolver (dynamic-sections.json lookup). */
  function urlRedirectFingerprint(raw) {
    const s = normalizeUrl(raw);
    let h1 = 2166136261 >>> 0;
    let h2 = 8159751279 >>> 0;
    for (let i = 0; i < s.length; i++) {
      const c = s.charCodeAt(i);
      h1 ^= c;
      h1 = Math.imul(h1, 16777619) >>> 0;
      h2 = (Math.imul(h2, 1099511627) ^ c) >>> 0;
    }
    const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz";
    function pack(n, len) {
      let x = n >>> 0;
      let out = "";
      for (let i = 0; i < len; i++) {
        out = alphabet[x % 36] + out;
        x = Math.floor(x / 36);
      }
      return out;
    }
    return pack(h1, 6) + pack(h2, 6);
  }

  function isGarbageLink(item) {
    const text = (item.name || item.title || "").toLowerCase();
    return text.includes("main home page") || text.includes("website ka main");
  }

  function openInternal(url, name) {
    const u = normalizeUrl(url);
    return `view.html?url=${encodeURIComponent(u)}&name=${encodeURIComponent(name)}`;
  }

  function buildRedirectUrl(targetUrl, label = "", sectionId = "") {
    const slug = slugifyTitle(label || targetUrl);
    if (!slug || slug === "official-link") return "";
    // Attach actual destination URL as ?ref= so job.html can use it
    // even when slug-based lookup in JSON fails (e.g. dailyupdates items)
    const dest = normalizeUrl(targetUrl);
    const refParam = dest ? "?ref=" + encodeURIComponent(dest) : "";
    return "/jobs/" + slug + "/" + refParam;
  }

  /** Redirect interstitial only for home section rows and view.html list items (not More / nav / etc.). */
  function isRedirectGatedLink(anchor) {
    if (!anchor || anchor.closest(".view-all")) return false;
    if (page === "index.html" || page === "") {
      return !!(anchor.closest("#dynamic-sections") && anchor.classList.contains("section-link"));
    }
    if (page === "view.html") {
      return !!anchor.closest("#links-list");
    }
    return false;
  }

  function shouldBypassRedirect(anchor, href) {
    if (!anchor || !href) return true;
    if (anchor.closest(".site-header") || anchor.closest("#mobileMenu")) return true;
    if (anchor.hasAttribute("download")) return true;
    // Skip redirect gate for direct job.html links (have data-bypass-gate or data-slug)
    if (anchor.hasAttribute("data-bypass-gate") || anchor.hasAttribute("data-slug")) return true;

    const raw = href.trim();
    if (!raw || raw === "#" || raw.startsWith("#")) return true;
    if (/^(javascript:|data:|blob:)/i.test(raw)) return true;

    let resolved;
    try {
      resolved = new URL(raw, location.href);
    } catch (_) {
      return true;
    }

    if (resolved.origin === location.origin && resolved.pathname.toLowerCase().endsWith("/redirect.html")) {
      return true;
    }
    return false;
  }

  function installGlobalRedirectGate() {
    if (page === "redirect.html") return;
    if (window.__redirectGateInstalled) return;
    window.__redirectGateInstalled = true;

    document.addEventListener("click", (e) => {
      const anchor = e.target.closest("a[href]");
      if (!anchor) return;

      if (e.defaultPrevented) return;
      if (e.button !== 0) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

      const href = anchor.getAttribute("href") || "";
      if (shouldBypassRedirect(anchor, href)) return;
      if (!isRedirectGatedLink(anchor)) return;

      const normalizedHref = normalizeUrl(href);
      if (!normalizedHref) return;
      if (/^(mailto:|tel:)/i.test(normalizedHref)) return;

      const target = (anchor.getAttribute("target") || "").trim().toLowerCase();
      const redirectLabel =
        anchor.getAttribute("data-redirect-label") ||
        anchor.getAttribute("aria-label") ||
        anchor.getAttribute("title") ||
        safe(anchor.textContent);
      const redirectUrl = buildRedirectUrl(normalizedHref, redirectLabel);
      if (!redirectUrl) return;

      e.preventDefault();

      if (target && target !== "_self") {
        window.open(redirectUrl, target, "noopener");
        return;
      }
      window.location.href = redirectUrl;
    }, true);
  }

  window.goBack = () => {
    if (window.history.length > 1) window.history.back();
    else window.location.href = "/";
  };

  function buildMobileMenu() {
    const nav = document.querySelector(".offcanvas-nav");
    if (!nav) return;
    /* If header.html already injected the new menu (has mob-acc-head elements),
       do NOT overwrite it — just return. The new menu is already correct. */
    if (nav.querySelector(".mob-acc-head") || nav.querySelector(".menu-icon-pill")) return;
    /* On index/homepage, mobileMenu is inline in HTML with full accordion menu.
       Do NOT overwrite it with the plain fallback. */
    const page = (location.pathname.split("/").pop() || "").toLowerCase();
    if (page === "index.html" || page === "" || page === "/") return;
    
    nav.innerHTML = `
      <a href="/">Home</a>
      <a href="/section/results/">Results</a>
      <a href="/govt-services/">CSC Services</a>
      <a href="/tools/">Tools</a>
      <a href="/helpdesk/">Helpdesk</a>

      <div class="offcanvas-group">
        <div class="offcanvas-group-title">Jobs</div>
        <a href="/category/study">Study wise jobs</a>
        <a href="/category/popular">Popular job categories</a>
        <a href="/category/state">State wise jobs</a>
      </div>

      <div class="offcanvas-group">
        <div class="offcanvas-group-title">Admissions</div>
        <a href="/category/admissions">Admissions</a>
        <a href="/category/admit-result">Admit Card / Result / Answer Key / Syllabus</a>
      </div>

      <div class="offcanvas-group">
        <div class="offcanvas-group-title">More</div>
        <a href="/category/khabar">Latest Khabar</a>
        <a href="/category/study-material">Study Material & Top Courses</a>
      </div>

      <div class="offcanvas-cta" id="header-links-mobile"></div>
    `;
  }

  // ✅ MOBILE HEADER BUTTON INJECTION
  function injectMobileHeaderBtns() {
    if (window.innerWidth > 980) return;
    const headerHost = document.getElementById("site-header") || document.querySelector(".site-header");
    if (!headerHost) return;

    const headerRow = headerHost.querySelector('.header-row');
    const headerActions = headerHost.querySelector('.header-actions');
    
    if (headerRow && headerActions && !document.getElementById('mobile-header-btns')) {
        const btns = document.createElement('div');
        btns.id = 'mobile-header-btns';
        btns.className = 'mobile-header-btns';
        btns.innerHTML = `
          <div class="mhb-row">
             <a href="/helpdesk/" class="mhb-btn">Helpdesk</a>
             <a href="/" class="mhb-btn">Home</a>
          </div>
          <a href="/tools/" class="mhb-btn mhb-full">Tools</a>
        `;
        headerRow.insertBefore(btns, headerActions);
    }
  }

  // ✅ SEARCH HIDER: Only hides truly duplicate/old search bars, never the main ones
  function safeHideOldSearchBars() {
    // DO NOT hide #siteSearchInput or #sectionSearchInput - these are the main search bars
    // that need to work on BOTH mobile and desktop. Hiding them breaks search functionality.
    // This function is intentionally left as a no-op to prevent search bars from being hidden.
  }

  async function injectHeaderFooter() {
    let headerHost = document.getElementById("site-header");
    if (!headerHost) headerHost = document.querySelector(".site-header");

    const footerHost = document.getElementById("site-footer");
    
    if (headerHost && (!headerHost.querySelector(".brand") || headerHost.innerHTML.trim() === "")) {
        // Use pre-fetched promise if available (set in <head> before script.js loads)
        // Falls back to direct fetch with retry on failure
        let html = null;
        try {
          if (window.__headerPromise) {
            html = await window.__headerPromise;
            window.__headerPromise = null; // use once
          }
          if (!html) {
            // Retry up to 3 times — protects against brief network hiccups on job pages
            for (let attempt = 0; attempt < 3; attempt++) {
              try {
                if (attempt > 0) await new Promise(r => setTimeout(r, attempt * 600));
                const r = await fetch("/header.html", { cache: "default" });
                if (r.ok) { html = await r.text(); break; }
              } catch (e) {}
            }
          }
        } catch (e) {}

        if (html) {
            headerHost.innerHTML = html;
            if (!headerHost.classList.contains("site-header")) {
                headerHost.classList.add("site-header");
            }
            buildMobileMenu();
            initOffcanvas();
            initDropdowns();
        } else {
            // All attempts failed — minimal fallback so page stays usable
            headerHost.innerHTML = '<div style="background:#1d3a6e;padding:10px 16px;display:flex;align-items:center;justify-content:space-between;"><a href="/" style="color:#fff;font-weight:900;font-size:1.1rem;text-decoration:none;">TOP <span style="color:#f59e0b;">SARKARI</span> JOBS</a><a href="/" style="color:#fff;font-size:.85rem;text-decoration:none;">&#8592; Home</a></div>';
        }
    } else if (headerHost && headerHost.querySelector(".brand")) {
        // Header already injected by early inline script — just init menus
        buildMobileMenu();
        initOffcanvas();
        initDropdowns();
    }

    injectMobileHeaderBtns();

    if (footerHost && footerHost.innerHTML.trim() === "") {
        try {
          const r = await fetch("/footer.html", { cache: "default" });
          if (r.ok) {
              footerHost.innerHTML = await r.text();
              if (!footerHost.classList.contains("site-footer")) footerHost.classList.add("site-footer");
          }
        } catch (_) {}
    }
  }

  async function loadHeaderLinks() {
    let data = { header_links: [], social_links: [] };
    try { data = await getJSON("/header_links.json"); } catch (_) {}

    const desktop = $("#header-links");
    const mobile = $("#header-links-mobile");
    const footerSocial = $("#footer-social-links");

    const links = Array.isArray(data.header_links) ? data.header_links : [];
    const socials = Array.isArray(data.social_links) ? data.social_links : [];

    if (desktop) {
      desktop.innerHTML = "";
      links.forEach((l) => {
        const a = document.createElement("a");
        a.className = "nav-link";
        a.href = normalizeUrl(l.link || l.url || "#");
        if (l.external) { a.target = "_blank"; a.rel = "noopener"; }
        a.textContent = l.name || "Link";
        desktop.appendChild(a);
      });
    }

    if (mobile) {
      mobile.innerHTML = "";
      links.forEach((l) => {
        const a = document.createElement("a");
        a.href = normalizeUrl(l.link || l.url || "#");
        if (l.external) { a.target = "_blank"; a.rel = "noopener"; }
        a.textContent = l.name || "Link";
        mobile.appendChild(a);
      });
    }

    if (footerSocial) {
      footerSocial.innerHTML = "";
      socials.forEach((s) => {
        const a = document.createElement("a");
        a.className = "nav-link";
        a.href = normalizeUrl(s.url || "#");
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = s.name || "Social";
        footerSocial.appendChild(a);
      });
    }
  }

  function initOffcanvas() {
    const btn = $("#menuBtn");
    const closeBtn = $("#closeMenuBtn");
    const menu = $("#mobileMenu");
    const overlay = $("#menuOverlay");
    if (!btn || !closeBtn || !menu || !overlay) return;

    const close = () => {
      menu.hidden = true;
      overlay.hidden = true;
      btn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
    };
    
    const open = () => {
      menu.hidden = false;
      overlay.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
    };

    btn.addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    overlay.addEventListener("click", close);
    menu.addEventListener("click", (e) => {
      if (e.target.closest("a")) close();
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 980) close();
      safeHideOldSearchBars(); 
    });
    window.__closeMenu = close;

    /* ── Mobile Menu Accordion ── */
    initMobileAccordion();

    /* ── Mobile Menu Search Filter ── */
    initMenuSearch();
  }

  function initMobileAccordion() {
    /* Remove old listeners by replacing with fresh ones via event delegation on menu */
    const menu = document.getElementById("mobileMenu");
    if (!menu || menu._accInit) return;
    menu._accInit = true;

    menu.addEventListener("click", function(e) {
      const btn = e.target.closest(".mob-acc-head");
      if (!btn) return;
      e.stopPropagation();
      const id   = btn.getAttribute("data-acc");
      const body = document.getElementById(id);
      if (!body) return;
      const isOpen = btn.classList.contains("open");
      /* Close all other accordions */
      menu.querySelectorAll(".mob-acc-head.open").forEach(function(b) {
        if (b !== btn) {
          b.classList.remove("open");
          const ob = document.getElementById(b.getAttribute("data-acc"));
          if (ob) ob.classList.remove("open");
        }
      });
      /* Toggle current */
      btn.classList.toggle("open", !isOpen);
      body.classList.toggle("open", !isOpen);
    });
  }

  function initMenuSearch() {
    const menu = document.getElementById("mobileMenu");
    if (!menu) return;
    const inp = menu.querySelector("#menuSearchInput");
    if (!inp || inp._searchInit) return;
    inp._searchInit = true;

    /* ── Build / reuse job search results container below the search box ── */
    let jobResultsBox = menu.querySelector("#menuJobResults");
    if (!jobResultsBox) {
      jobResultsBox = document.createElement("div");
      jobResultsBox.id = "menuJobResults";
      jobResultsBox.style.cssText = [
        "display:none",
        "max-height:260px",
        "overflow-y:auto",
        "background:#fff",
        "border-top:1px solid #e2e8f0",
        "padding:4px 0"
      ].join(";");
      const searchWrap = menu.querySelector(".offcanvas-search");
      if (searchWrap) searchWrap.after(jobResultsBox);
    }

    /* ── Load job data once (lazy) ── */
    let jobSearchData = null;
    async function ensureJobData() {
      if (jobSearchData) return jobSearchData;
      jobSearchData = [];
      try {
        /* Smart loading: full chunk for category pages, summary for homepage */
        // All data comes from Complete_Jobs_Full_Data.json only
        const complete = await getJSON("/data/Complete_Jobs_Full_Data.json").catch(() => null);
        const merged = complete ? { jobs: (complete.sarkari_data || {}).jobs || [] } : null;
        const slugify = t => (t || "").toLowerCase().replace(/[^a-z0-9\s-]/g, "").replace(/[\s-]+/g, "-").slice(0, 120).replace(/^-+|-+$/g, "");
        if (merged && Array.isArray(merged.jobs)) {
          merged.jobs.forEach(j => {
            if (!j.title) return;
            const slug = j.slug || slugify(j.title);
            jobSearchData.push({ name: j.title.trim(), href: slug ? "/jobs/" + slug + "/" : "#" });
          });
        }
        if (complete && typeof complete === "object") {
          Object.keys(complete).forEach(k => {
            if (!Array.isArray(complete[k])) return;
            complete[k].forEach(i => {
              const bd = i.basic_details || {};
              const title = bd.job_title || bd.post_name || i.title || i.name || "";
              if (!title) return;
              const slug = i.slug || slugify(title);
              jobSearchData.push({ name: title.trim(), href: slug ? "/jobs/" + slug + "/" : "#" });
            });
          });
        }
        /* Deduplicate by name */
        const seen = new Set();
        jobSearchData = jobSearchData.filter(j => {
          if (seen.has(j.name)) return false;
          seen.add(j.name); return true;
        });
      } catch (_) {}
      return jobSearchData;
    }

    inp.addEventListener("input", async function() {
      const q = this.value.trim().toLowerCase();

      /* ── 1. Filter nav links (same as before) ── */
      menu.querySelectorAll(".offcanvas-nav > a").forEach(function(a) {
        a.style.display = (!q || a.textContent.toLowerCase().includes(q)) ? "" : "none";
      });
      menu.querySelectorAll(".mob-acc-body a").forEach(function(a) {
        a.style.display = (!q || a.textContent.toLowerCase().includes(q)) ? "" : "none";
      });
      menu.querySelectorAll(".mob-acc-body").forEach(function(b) {
        b.classList.toggle("open", !!q);
      });
      menu.querySelectorAll(".mob-acc-head").forEach(function(b) {
        b.classList.toggle("open", !!q);
      });

      /* ── 2. Search job titles ── */
      if (!q || q.length < 2) {
        jobResultsBox.style.display = "none";
        jobResultsBox.innerHTML = "";
        return;
      }

      const data = await ensureJobData();
      const tokens = q.split(/\s+/).filter(t => t.length);
      const hits = data.filter(j => tokens.every(t => j.name.toLowerCase().includes(t))).slice(0, 12);

      jobResultsBox.innerHTML = "";
      if (!hits.length) {
        jobResultsBox.innerHTML = '<div style="padding:10px 16px;font-size:.78rem;color:#94a3b8;text-align:center;">No job found. Try: SSC, Railway, Bank…</div>';
      } else {
        hits.forEach(h => {
          const a = document.createElement("a");
          a.href = h.href;
          a.style.cssText = "display:flex;align-items:center;gap:9px;padding:9px 14px;font-size:.78rem;font-weight:600;color:#1e293b;text-decoration:none;border-bottom:1px solid #f1f5f9;transition:background .12s;";
          a.innerHTML = `<i class="fa-solid fa-briefcase" style="color:#2563eb;font-size:.72rem;flex-shrink:0;"></i><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${h.name}</span>`;
          a.addEventListener("mouseover", () => { a.style.background = "#eff6ff"; });
          a.addEventListener("mouseout", () => { a.style.background = ""; });
          jobResultsBox.appendChild(a);
        });
      }
      jobResultsBox.style.display = "block";
    });
  }

  function initDropdowns() {
    const dds = $$("[data-dd]");
    if (!dds.length) return;
    const canHover = () => window.matchMedia("(hover:hover) and (pointer:fine)").matches;
    const timers = new WeakMap();

    const setOpen = (dd, open) => {
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if (!btn || !menu) return;
      if (open) {
        menu.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
      } else {
        menu.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
      }
    };

    const clearTimer = (dd) => {
      const t = timers.get(dd);
      if (t) clearTimeout(t);
      timers.delete(dd);
    };
    const closeAll = () => {
      dds.forEach((dd) => { clearTimer(dd); setOpen(dd, false); });
    };
    const scheduleClose = (dd) => {
      clearTimer(dd);
      timers.set(dd, setTimeout(() => setOpen(dd, false), 180));
    };

    dds.forEach((dd) => {
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if (!btn || !menu) return;

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const isOpen = menu.classList.contains("open");
        closeAll();
        if (!isOpen) setOpen(dd, true);
      });
      btn.addEventListener("mouseenter", () => {
        if (!canHover()) return;
        clearTimer(dd);
        closeAll();
        setOpen(dd, true);
      });
      btn.addEventListener("mouseleave", () => {
        if (!canHover()) return;
        scheduleClose(dd);
      });
      menu.addEventListener("mouseenter", () => {
        if (!canHover()) return;
        clearTimer(dd);
        setOpen(dd, true);
      });
      menu.addEventListener("mouseleave", () => {
        if (!canHover()) return;
        scheduleClose(dd);
      });
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest("[data-dd]")) closeAll();
    });
  }

  function initFAQ() {
    $$(".faq-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const expanded = btn.getAttribute("aria-expanded") === "true";
        $$(".faq-btn").forEach((b) => {
          b.setAttribute("aria-expanded", "false");
          const p = b.parentElement.querySelector(".faq-panel");
          if (p) p.hidden = true;
        });
        if (!expanded) {
          btn.setAttribute("aria-expanded", "true");
          const p = btn.parentElement.querySelector(".faq-panel");
          if (p) p.hidden = false;
        }
      });
    });
  }

  async function renderHomepageSections() {
    // DUPLICATE FIX: if the TSJ9 grid (#sr-sections-grid) is present, it is the
    // single source of truth for homepage section cards. Skip the legacy renderer
    // to avoid rendering every section twice.
    if (document.getElementById("sr-sections-grid")) return;
    const wrap = $("#dynamic-sections");
    if (!wrap) return;

    let data = { sections: [] };
    let fetchFailed = false;
    try { data = await getJobsSections(); }
    catch (_) { fetchFailed = true; }

    // ISSUE-009: surface a visible message when the data file failed to load
    // instead of silently rendering a blank homepage.
    // FIX: Don't clear innerHTML until data successfully loaded — prevents
    // pre-rendered SSG cards from disappearing on slow/failed fetch.
    if (fetchFailed || !Array.isArray(data.sections) || !data.sections.length) {
      if (!wrap.hasChildNodes()) {
        // Only show error if there's no pre-rendered content already
        const note = document.createElement("div");
        note.className = "seo-block";
        note.style.margin = "16px 0";
        note.innerHTML = fetchFailed
          ? "<strong>Couldn't load the latest updates.</strong><div style=\"margin-top:6px;color:var(--muted);\">Please check your connection and refresh the page.</div>"
          : "<strong>No updates to show right now.</strong>";
        wrap.appendChild(note);
      }
      if (fetchFailed) return;
      // If sections empty but no fetch error, keep existing pre-rendered content
      return;
    }

    // Data loaded successfully — now safe to clear and re-render
    wrap.innerHTML = "";

    // ── RENDER ALL SECTIONS IMMEDIATELY — no lazy scroll needed for job cards ──
    const sections = data.sections || [];
    const INITIAL_COUNT = 999; // render ALL sections instantly (no lazy loading)

    function renderSection(sec) {
      const title = safe(sec.title) || "Updates";
      const baseColor = safe(sec.color) || "#0284c7";
      const icon = safe(sec.icon) || "fa-solid fa-briefcase";

      const bgStyle = baseColor.includes("gradient") 
        ? `background: ${baseColor};` 
        : `background-color: ${baseColor}; background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.18) 0%, rgba(0, 0, 0, 0.15) 100%);`;

      const sectionKey = safe(sec.id) || safe(sec.title);
      let moreHref = "";
      if (safe(sec.viewMoreUrl)) {
        moreHref = openInternal(sec.viewMoreUrl, title);
      } else if (safe(sec.viewMoreType).toLowerCase() === "list" && sectionKey) {
        moreHref = `/section/${sectionKey.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')}/`;
      }

      const card = document.createElement("article");
      card.className = "section-card";
      card.innerHTML = `
        <div class="section-head" style="${bgStyle} text-shadow: 0 1px 3px rgba(0,0,0,0.35); border-bottom: 2px solid rgba(255,255,255,0.15);">
          <div class="left">
            <i class="${icon}" style="color:#fff;opacity:.9;font-size:1rem;"></i>
            <span style="font-size:.84rem;letter-spacing:.04em;text-transform:uppercase;font-weight:900;color:#fff;">${title}</span>
          </div>
          ${moreHref ? `<a class="view-all-head" href="${moreHref}">View All</a>` : ""}
        </div>
        <div class="section-body">
          <div class="section-list-wrap">
            <div class="section-list"></div>
          </div>
          ${moreHref ? `<a class="view-all" href="${moreHref}">More <i class="fa-solid fa-arrow-right"></i></a>` : ""}
        </div>
      `;

      const list = $(".section-list", card);
      const listWrap = $(".section-list-wrap", card);
      const items = Array.isArray(sec.items)
        ? sec.items.filter(i => !isGarbageLink(i)).slice(0, 10)
        : [];

      items.forEach((it, _idx) => {
        const name = safe(it.name) || "Open";
        // Build URL: prefer explicit url/link, fallback to slug-based job.html
        let url = it.url || it.link || "";
        // If item has an internal slug, ALWAYS use /jobs/{slug}/ as the link
        if (it.slug) {
          url = "/jobs/" + it.slug + "/";
        } else if (name && name.length > 3) {
          // FIX: Generate slug from title for state-wise items that only have external URL
          const genSlug = name.toLowerCase()
            .replace(/[^a-z0-9\s-]/g, '')
            .replace(/[\s-]+/g, '-')
            .replace(/^-+|-+$/g, '')
            .slice(0, 60);
          if (genSlug) {
            url = "/jobs/" + genSlug + "/";
            it._genSlug = genSlug;
            it._externalFallback = it.url || it.link || "";
          }
        }
        if (!url) return;

        const external = !!it.external;
        const a = document.createElement("a");
        a.className = "section-link";
        /* If URL is a job.html link (from slug), use directly — bypass redirect gate */
        if (url.startsWith("/jobs/") || url.startsWith("job.html")) {
          a.href = url;
          a.setAttribute("data-bypass-gate", "1");
          if (it.slug) a.setAttribute("data-slug", it.slug);
        } else {
          a.href = buildRedirectUrl(url, name, sectionKey) || normalizeUrl(url);
        }
        a.setAttribute("data-redirect-label", name);
        a.setAttribute("title", name);
        a.setAttribute("aria-label", name);
        if (external) { a.target = "_blank"; a.rel = "noopener"; }
        const rawDate = safe(it.date || "");
        const _db1 = formatDateBadge(rawDate);
        const _dh1 = _db1 ? `<span class="d ${_db1.colorClass}"><i class="fa-regular fa-calendar-days"></i> ${_db1.colorClass === 'd-expired' ? 'Closed' : _db1.display}</span>` : "";
        a.innerHTML = `<span class="sn-badge">${_idx+1}</span><span class="t">${name}${_dh1}</span>`;
        list.appendChild(a);

        // ✅ SEARCH INDEX: sirf internal job.html links push karo (external nav/tools skip)
        if (url && (url.startsWith("/jobs/") || url.startsWith("job.html"))) {
          (window.tsjSearchIndex = window.tsjSearchIndex || []).push({
            title: name,
            slug: url,
            dept: title,
            qual: it.qualification || "",
            state: it.state || "All India",
            cat: sectionKey,
            tags: name + " " + sectionKey + " " + title + " sarkari naukri 2026",
            lastDate: rawDate,
            icon: (icon.split(" ").find(c => c.startsWith("fa-") && c !== "fa-solid") || "fa-briefcase"),
            lastUpdated: it.last_updated || it.updated_at || new Date().toISOString(),
            sectionSource: title,
          });
        }
      });

      wrap.appendChild(card);

      // Scroll-end shadow detection — hide bottom fade when scrolled to end
      if (items.length > 5 && listWrap) {
        list.addEventListener("scroll", () => {
          const atEnd = list.scrollHeight - list.scrollTop <= list.clientHeight + 8;
          listWrap.classList.toggle("scrolled-to-end", atEnd);
        }, { passive: true });
      } else if (listWrap) {
        listWrap.classList.add("scrolled-to-end"); // no scroll needed, no shadow
      }
    } // end renderSection()

    // Render first INITIAL_COUNT sections immediately (above fold)
    sections.slice(0, INITIAL_COUNT).forEach(renderSection);

    // Render remaining sections progressively using IntersectionObserver
    if (sections.length > INITIAL_COUNT) {
      const remaining = sections.slice(INITIAL_COUNT);
      let remainingIndex = 0;

      // Create sentinel element at end of wrap
      const sentinel = document.createElement("div");
      sentinel.style.cssText = "height:1px;width:100%;";
      wrap.appendChild(sentinel);

      if ("IntersectionObserver" in window) {
        const obs = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            // Render next batch of sections (4 at a time)
            const batch = remaining.slice(remainingIndex, remainingIndex + 4);
            batch.forEach(renderSection);
            remainingIndex += 4;
            if (remainingIndex >= remaining.length) {
              obs.disconnect();
              sentinel.remove();
            }
          });
        }, { rootMargin: "300px" });
        obs.observe(sentinel);
      } else {
        // Fallback: render all
        remaining.forEach(renderSection);
        sentinel.remove();
      }
    }
  }

  /* ─────────────────────────────────────────────────────────────────
     renderDailyUpdatesSections()
     Loads dailyupdates.json and appends each section as a section-card
     BELOW the existing #dynamic-sections cards.
     • Fully automatic: add/remove sections in JSON → auto updates homepage.
     • Uses a separate container #daily-updates-sections so it never
       overwrites the jobs cards above.
  ───────────────────────────────────────────────────────────────── */
  function buildSectionCard(sec, wrap) {
    const title     = safe(sec.title) || "Updates";
    const baseColor = safe(sec.color) || "#0284c7";
    const icon      = safe(sec.icon)  || "fa-solid fa-briefcase";

    const bgStyle = baseColor.includes("gradient")
      ? `background: ${baseColor};`
      : `background-color: ${baseColor}; background-image: linear-gradient(135deg, rgba(255,255,255,0.18) 0%, rgba(0,0,0,0.15) 100%);`;

    const sectionKey = safe(sec.id) || safe(sec.title);
    let moreHref = "";
    if (safe(sec.viewMoreUrl)) {
      moreHref = openInternal(sec.viewMoreUrl, title);
    } else if (safe(sec.viewMoreType).toLowerCase() === "list" && sectionKey) {
      moreHref = `/section/${sectionKey.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')}/`;
    }

    const card = document.createElement("article");
    card.className = "section-card";
    card.innerHTML = `
      <div class="section-head" style="${bgStyle} text-shadow: 0 1px 3px rgba(0,0,0,0.35); border-bottom: 2px solid rgba(255,255,255,0.15);">
        <div class="left">
          <i class="${icon}" style="color:#fff;opacity:.9;font-size:1rem;"></i>
          <span style="font-size:.84rem;letter-spacing:.04em;text-transform:uppercase;font-weight:900;color:#fff;">${title}</span>
        </div>
        ${moreHref ? `<a class="view-all-head" href="${moreHref}">View All</a>` : ""}
      </div>
      <div class="section-body">
        <div class="section-list-wrap">
          <div class="section-list"></div>
        </div>
        ${moreHref ? `<a class="view-all" href="${moreHref}">More <i class="fa-solid fa-arrow-right"></i></a>` : ""}
      </div>
    `;

    const list     = $(".section-list", card);
    const listWrap = $(".section-list-wrap", card);
    const items = Array.isArray(sec.items)
      ? sec.items.filter(i => !isGarbageLink(i)).slice(0, 10)
      : [];

    items.forEach((it, _idx) => {
      const name = safe(it.name) || "Open";
      let url = it.url || it.link || "";
      // FIX: Generate internal /jobs/slug/ URL from title when no slug exists
      // This ensures state-wise items open a detail page instead of redirecting externally
      if (it.slug) {
        url = "/jobs/" + it.slug + "/";
      } else if (name && name.length > 3) {
        // Generate slug from title — same logic as slugify in data pipeline
        const genSlug = name.toLowerCase()
          .replace(/[^a-z0-9\s-]/g, '')
          .replace(/[\s-]+/g, '-')
          .replace(/^-+|-+$/g, '')
          .slice(0, 60);
        if (genSlug) {
          url = "/jobs/" + genSlug + "/";
          it._genSlug = genSlug;
          it._externalFallback = it.url || it.link || "";
        }
      }
      if (!url) return;

      const external = !!it.external;
      const a = document.createElement("a");
      a.className = "section-link";
      if (url.startsWith("/jobs/") || url.startsWith("job.html")) {
        a.href = url;
        a.setAttribute("data-bypass-gate", "1");
        if (it.slug) a.setAttribute("data-slug", it.slug);
      } else {
        a.href = buildRedirectUrl(url, name, sectionKey) || normalizeUrl(url);
      }
      a.setAttribute("data-redirect-label", name);
      a.setAttribute("title", name);
      a.setAttribute("aria-label", name);
      if (external) { a.target = "_blank"; a.rel = "noopener"; }

      const rawDate = safe(it.date || "");
      const _db2 = formatDateBadge(rawDate);
      const _dh2 = _db2 ? `<span class="d ${_db2.colorClass}"><i class="fa-regular fa-calendar-days"></i> ${_db2.display}</span>` : "";
      a.innerHTML = `<span class="sn-badge">${_idx+1}</span><span class="t">${name}${_dh2}</span>`;
      list.appendChild(a);

      // ✅ SEARCH INDEX: sirf internal job.html links push karo (external nav/tools skip)
      if (url && (url.startsWith("/jobs/") || url.startsWith("job.html"))) {
        (window.tsjSearchIndex = window.tsjSearchIndex || []).push({
          title: name,
          slug: url,
          dept: title,
          qual: "",
          state: "All India",
          cat: sectionKey,
          tags: name + " " + sectionKey + " " + title + " sarkari naukri 2026",
          lastDate: rawDate,
          icon: (icon.split(" ").find(c => c.startsWith("fa-") && c !== "fa-solid") || "fa-briefcase"),
          lastUpdated: it.last_updated || it.updated_at || new Date().toISOString(),
          sectionSource: title,
        });
      }
    });

    wrap.appendChild(card);

    if (items.length > 5 && listWrap) {
      list.addEventListener("scroll", () => {
        const atEnd = list.scrollHeight - list.scrollTop <= list.clientHeight + 8;
        listWrap.classList.toggle("scrolled-to-end", atEnd);
      }, { passive: true });
    } else if (listWrap) {
      listWrap.classList.add("scrolled-to-end");
    }
  }

  async function renderDailyUpdatesSections() {
    // Only run on homepage
    if (!(page === "index.html" || page === "")) return;
    // DUPLICATE FIX: TSJ9 grid already renders the daily-update sections
    // (Govt Scheme, ImportantCSC PDF/link, Top 20, Today Updates). Skip to avoid dupes.
    if (document.getElementById("sr-sections-grid")) return;

    // Find or create the daily-updates container (placed right after #dynamic-sections)
    let dailyWrap = document.getElementById("daily-updates-sections");
    if (!dailyWrap) {
      const dynSec = document.getElementById("dynamic-sections");
      if (!dynSec) return;
      dailyWrap = document.createElement("div");
      dailyWrap.id = "daily-updates-sections";
      dailyWrap.className = "dynamic-sections-row";
      dynSec.parentNode.insertBefore(dailyWrap, dynSec.nextSibling);
    }
    dailyWrap.innerHTML = "";

    let data;
    try {
      data = await getJSON("dailyupdates.json");
    } catch (_) {
      return; // silently skip if file not found
    }

    const sections = Array.isArray(data.sections) ? data.sections : [];
    // Render first 2 immediately, rest lazily
    const INITIAL = 999; // render ALL daily sections immediately
    sections.slice(0, INITIAL).forEach(sec => buildSectionCard(sec, dailyWrap));

    if (sections.length > INITIAL) {
      const remaining = sections.slice(INITIAL);
      let idx = 0;
      const sentinel = document.createElement("div");
      sentinel.style.cssText = "height:1px;width:100%;";
      dailyWrap.appendChild(sentinel);
      if ("IntersectionObserver" in window) {
        const obs = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            remaining.slice(idx, idx + 4).forEach(sec => buildSectionCard(sec, dailyWrap));
            idx += 4;
            if (idx >= remaining.length) { obs.disconnect(); sentinel.remove(); }
          });
        }, { rootMargin: "400px" });
        obs.observe(sentinel);
      } else {
        remaining.forEach(sec => buildSectionCard(sec, dailyWrap));
        sentinel.remove();
      }
    }
  }

  // ✅ DISABLED — home-quicklinks-wrap section permanently removed from all pages
  async function renderHomeQuickLinks() { return; }
  async function _renderHomeQuickLinks_bak() {
    const isHome = (page === "index.html" || page === "");
    
    let wrap = document.getElementById("home-quicklinks-wrap");
    let host = document.getElementById("home-links");
    
    if (!wrap) {
      wrap = document.createElement("section");
      wrap.id = "home-quicklinks-wrap";
      wrap.className = "home-quicklinks"; // Wrapper is always visible for grid/search
      
      host = document.createElement("div");
      host.id = "home-links";
      // ✅ Pill boxes display natively on desktop. On mobile inner pages, they hide!
      host.className = isHome ? "home-links" : "home-links hidden-on-inner";
      wrap.appendChild(host);
      
      const mainEl = document.getElementById("main") || document.querySelector("main") || document.body;
      if (mainEl && mainEl.parentNode) {
          mainEl.parentNode.insertBefore(wrap, mainEl);
      }
    }

    if (!document.getElementById("home-quicklinks-style")) {
      const style = document.createElement("style");
      style.id = "home-quicklinks-style";
      style.textContent = `
        .home-quicklinks { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 0; }
        
        /* DESKTOP VIEW */
        .home-links { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: center; }
        
        .home-link-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 8px 16px;
          border-radius: 99px;
          color: #fff;
          font-weight: 700;
          font-size: 14px;
          text-decoration: none;
          line-height: 1.2;
          box-shadow: 0 4px 10px rgba(0,0,0,0.08);
          border: 1px solid rgba(255,255,255,0.2);
          white-space: nowrap;
          transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
        }
        .home-link-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 15px rgba(0,0,0,0.15);
          filter: brightness(1.05);
        }
        .home-link-btn:active { transform: translateY(0); }
        
        /* ✅ PREMIUM MOBILE APP OVERRIDES */
        @media (max-width: 980px) {
          .home-quicklinks { padding-top: 16px; padding-bottom: 6px; }
          .hidden-on-inner { display: none !important; }
          
          /* The 4-Column Grid */
          .mobile-nav-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            grid-auto-rows: 1fr;
            gap: 8px;
            margin-bottom: 10px;
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            padding: 12px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.6);
            box-shadow: 0 8px 24px rgba(2, 132, 199, 0.06);
          }
          .grid-nav-btn {
            background: #ffffff;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 800;
            text-align: center;
            padding: 12px 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1.3;
            text-decoration: none;
            word-break: break-word;
            transition: transform 0.2s ease;
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
            border: 1px solid #e2e8f0;
          }
          .grid-nav-btn:active { transform: scale(0.95); }
          
          /* UNIFORM OUTLINE ROW THEMES (As requested) */
          .grid-nav-btn.solid-blue { background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 4px 10px rgba(37,99,235,0.25); border: 1px solid #1e40af; text-shadow: 0 1px 1px rgba(0,0,0,0.2); }
          .grid-nav-btn.outline-blue { background: #f0f9ff; color: #1d4ed8; border: 1px solid #bfdbfe; font-weight: 800; }
          
          .grid-nav-btn.outline-purple { background: #faf5ff; color: #7e22ce; border: 1px solid #e9d5ff; font-weight: 800; }
          .grid-nav-btn.outline-orange { background: #fff7ed; color: #ea580c; border: 1px solid #fed7aa; font-weight: 800; }
          .grid-nav-btn.solid-green { background: linear-gradient(135deg, #10b981, #059669); color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 4px 10px rgba(16,185,129,0.25); border: 1px solid #047857; text-shadow: 0 1px 1px rgba(0,0,0,0.2); }

          /* ✅ PERFECT 3D EMBOSSED PILLS: Flex-grow automatically stretches to lock together! */
          .home-links { 
            display: flex;
            flex-wrap: wrap;
            gap: 8px 6px; 
            justify-content: center; 
            align-content: stretch;
            padding: 0 6px; 
            margin-bottom: 0px; 
          }
          .home-link-btn { 
            flex: 1 1 auto; 
            padding: 10px 12px; 
            font-size: 13px; 
            text-align: center;
            justify-content: center;
            margin: 0;
            min-width: 28%; 
            border-radius: 12px;
            /* Beautiful 3D bevel from your reference */
            box-shadow: inset 0px 4px 6px rgba(255,255,255,0.35), inset 0px -4px 6px rgba(0,0,0,0.25), 0 4px 6px rgba(0,0,0,0.15);
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
            border: none;
            letter-spacing: 0.2px;
          }
          
          /* Custom Bottom Search exactly like screenshot */
           .mobile-bottom-search {
           background: #ffffff;
           border: 1px solid #e2e8f0;
           padding: 20px 14px;
           margin-top: 6px;
           margin-bottom: 6px;
           border-radius: 16px;
           text-align: center;
           box-shadow: 0 8px 24px rgba(0,0,0,0.06);
           }
          .mobile-bottom-search h3 {
            font-size: 15px;
            font-weight: 900;
            margin: 0 0 14px;
            color: #0f172a;
            letter-spacing: -0.2px;
          }
          .mbs-row {
            display: flex;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            overflow: hidden;
            background: #f8fafc;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
          }
          .mbs-row input {
            flex: 1;
            height: 46px;
            border: none;
            background: transparent;
            padding: 0 14px;
            font-size: 14px;
            outline: none;
            color: #0f172a;
          }
          .mbs-row input:focus { background: #fff; border-color: #0ea5e9; }
          .mbs-row button {
            background: linear-gradient(135deg, #0ea5e9, #4f46e5);
            color: #fff;
            border: none;
            padding: 0 20px;
            font-weight: 800;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
          }
        }
      `;
      document.head.appendChild(style);
    }

    let data = null;
    try { data = await getJSON("/header_links.json"); } catch (_) {}

    let waLink = "https://whatsapp.com/channel/0029VaA2aD4FCCoW3q8y6x25";
    if (data && data.header_links) {
        const waObj = data.header_links.find(l => safe(l.name).toLowerCase().includes("whatsapp"));
        if (waObj && (waObj.url || waObj.link)) waLink = waObj.url || waObj.link;
    }
    
    // ✅ INJECT CUSTOM APP GRID (Matching Exact Uniform Outlines & Link)
    if (wrap && !document.getElementById("mobile-nav-grid")) {
        const mobileNavWrap = document.createElement("div");
        mobileNavWrap.id = "mobile-nav-grid";
        mobileNavWrap.className = "mobile-nav-grid";

        const mLinks = [
            // Row 1 (Blue)
            { name: "Latest Jobs", url: "/section/latest-jobs/", cls: "outline-blue" },
            { name: "Study wise jobs", url: "category.html?group=study", cls: "outline-blue" },
            { name: "Categories wise jobs", url: "category.html?group=popular", cls: "outline-blue" },
            { name: "State wise Jobs", url: "category.html?group=state", cls: "outline-blue" },
            
            // Row 2 (Purple)
            { name: "Admissions", url: "category.html?group=admissions", cls: "outline-purple" },
            { name: "Resume/CV Maker", url: "resume-maker.html" }, 
            { name: "CSC Services", url: "govt-services.html", cls: "outline-purple" },
            { name: "Study Material", url: "category.html?group=study-material", cls: "outline-purple" },
            
            // Row 3 (Orange + Solid Green WhatsApp)
            { name: "Results", url: "/section/results/", cls: "outline-orange" },
            { name: "Admit Card", url: "category.html?group=admit-result", cls: "outline-orange" },
            { name: "Latest Khabar", url: "category.html?group=khabar", cls: "outline-orange" },
            { name: "Join WhatsApp", url: waLink, cls: "solid-green" } 
        ];

        mLinks.forEach(l => {
            const a = document.createElement("a");
            a.className = `grid-nav-btn ${l.cls}`;
            a.href = l.url;
            a.innerHTML = l.name;
            mobileNavWrap.appendChild(a);
        });

        wrap.insertBefore(mobileNavWrap, wrap.firstChild);
    }

    // Process pill links (Will be hidden automatically on inner pages by CSS)
    const links = Array.isArray(data?.home_links) ? data.home_links : [];
    if (links.length) {
      
      const excludeList = [
          "latest jobs", "study wise", "categories wise", "popular categories", "state wise",
          "admissions", "admission", "resume", "cv maker", "csc", "study material",
          "results", "result", "admit card", "khabar", "helpdesk", "home", "tools", "whatsapp"
      ];

      // ✅ BRAND NEW PREMIUM APP COLORS FOR PILLS (iOS Inspired Gradients)
      const premiumGradients = [
          "linear-gradient(135deg, #3b82f6, #2563eb)", // Blue
          "linear-gradient(135deg, #8b5cf6, #7c3aed)", // Violet
          "linear-gradient(135deg, #10b981, #059669)", // Emerald
          "linear-gradient(135deg, #f59e0b, #d97706)", // Amber
          "linear-gradient(135deg, #ec4899, #db2777)", // Pink
          "linear-gradient(135deg, #0ea5e9, #0284c7)", // Sky
          "linear-gradient(135deg, #f43f5e, #e11d48)", // Rose
          "linear-gradient(135deg, #6366f1, #4f46e5)"  // Indigo
      ];

      let validLinks = [];
      links.forEach((l) => {
        let name = safe(l?.name);
        if (name.includes("लाडो लक्ष्मी योजना: पैसा आया है या नहीं आया यहाँ से चेक करें")) {
            name = "लाडो लक्ष्मी योजना: पैसा आया है या नहीं - यहाँ से चेक करें";
        }
        const nLower = name.toLowerCase().trim();
        if (excludeList.some(ex => nLower.includes(ex))) return;
        
        const url = safe(l?.url || l?.link);
        if (!name || !url) return;
        
        validLinks.push({ ...l, name: name, url: url });
      });

      // 1. Extract Top Headlines so it's always forced to the #1 top position
      let topHeadlineIndex = validLinks.findIndex(l => l.name.toLowerCase().includes("headlines"));
      let topHeadline = null;
      if (topHeadlineIndex > -1) {
          topHeadline = validLinks.splice(topHeadlineIndex, 1)[0];
      }

      // 2. Pair shuffling algorithm (mixes long and short names so flex automatically wraps them beautifully)
      validLinks.sort((a, b) => a.name.length - b.name.length);
      let mixedLinks = [];
      let left = 0; let right = validLinks.length - 1;
      while (left <= right) {
          if (left === right) { mixedLinks.push(validLinks[left]); break; }
          mixedLinks.push(validLinks[right]); 
          mixedLinks.push(validLinks[left]);  
          right--; left++;
      }

      const finalLinks = topHeadline ? [topHeadline, ...mixedLinks] : mixedLinks;

      host.innerHTML = "";
      finalLinks.forEach((l, index) => {
        const a = document.createElement("a");
        a.className = "home-link-btn";
        a.href = normalizeUrl(l.url);
        if (l.external) { a.target = "_blank"; a.rel = "noopener"; }
        
        // Top Headlines gets special bright red, the rest use our beautiful new palette
        if (l.name.toLowerCase().includes("headlines")) {
             a.style.background = "linear-gradient(135deg, #ef4444, #dc2626)";
             a.style.width = "100%"; 
        } else {
             a.style.background = premiumGradients[index % premiumGradients.length];
        }
        
        const icon = safe(l.icon);
        if (icon) a.innerHTML = `<i class="${icon}" style="color:#fff;opacity:.9;font-size:1rem;"></i><span>${l.name}</span>`;
        else a.textContent = l.name;
        host.appendChild(a);
      });
    }

    // ✅ INJECT PERFECT BOTTOM SEARCH BAR
    if (wrap && !document.getElementById("mobile-bottom-search")) {
        const mbs = document.createElement("div");
        mbs.id = "mobile-bottom-search";
        mbs.className = "mobile-bottom-search";
        mbs.innerHTML = `
            <h3>Search Sarkari नौकरियाँ - Just Click Below</h3>
            <div class="mbs-row">
                <input id="mobileBottomSearchInput" type="search" placeholder="Search job categories, results, admit cards..." autocomplete="off" />
                <button type="button" id="mobileBottomSearchBtn"><i class="fa-solid fa-magnifying-glass"></i> Search</button>
            </div>
            <div id="mobileBottomSearchResults" class="search-results" style="margin-top: 10px; text-align: left;"></div>
        `;
        wrap.appendChild(mbs);
    }
  }

  function removeHomeMainPageCtaLinks() {
    if (!(page === "index.html" || page === "")) return;
    const wrap = document.getElementById("dynamic-sections");
    if (!wrap) return;

    const needles = [
      "╰┈➤🏠Website का Main Home Page खोलने के लिए यहाँ क्लिक करें",
      "Website का Main Home Page खोलने के लिए यहाँ क्लिक करें",
      "Main Home Page खोलने के लिए यहाँ क्लिक करें",
      "Website का Main Home Page",
    ];

    const els = Array.from(wrap.querySelectorAll("a, button"));
    els.forEach((el) => {
      const t = safe(el.textContent).replace(/\s+/g, " ");
      if (!t) return;
      if (needles.some((n) => t.includes(n))) el.remove();
    });
  }

  // Category Pages
  async function initCategoryPage() {
    if (page !== "category.html") return;
    const params = new URLSearchParams(location.search || "");
    const group = safe(params.get("group")).toLowerCase();

    const titleEl = $("#categoryTitle") || $("h1");
    let gridEl = $("#categoryGrid") || $(".section-list");
    const emptyEl = $("#categoryEmpty");

    if (!gridEl) {
      const main = $("#main") || $("main") || document.body;
      const wrap = document.createElement("div");
      wrap.className = "section-list";
      main.appendChild(wrap);
      gridEl = wrap;
    }

    const groupMeta = { study: "Study wise jobs", popular: "Popular job categories", state: "State wise jobs", admissions: "Admissions", "admit-result": "Admit Card / Result", khabar: "Latest Khabar", "study-material": "Study Material & Top Courses" };
    if (titleEl) titleEl.textContent = groupMeta[group] || "Browse Categories";

    // ISSUE-006: with no/unknown group, render a directory of valid groups
    // instead of a blank page.
    if (!group || !(group in groupMeta)) {
      gridEl.innerHTML = "";
      Object.entries(groupMeta).forEach(([slug, label]) => {
        const a = document.createElement("a");
        a.className = "section-link";
        a.href = "/category/" + encodeURIComponent(slug);
        a.innerHTML = `<div class="t">${label}</div><div class="d">Browse this category</div>`;
        gridEl.appendChild(a);
      });
      const desc = $("#categoryDesc");
      if (desc) desc.textContent = "Pick a category to see related government jobs, admit cards, results and study material.";
      return;
    }

    let data;
    try { data = await getJSON("/jobs.json"); } catch (_) {
      gridEl.innerHTML = "";
      return;
    }

    const top = Array.isArray(data.top_jobs) ? data.top_jobs : [];
    const left = Array.isArray(data.left_jobs) ? data.left_jobs : [];
    const right = Array.isArray(data.right_jobs) ? data.right_jobs : [];

    const isHeader = (x) => x && typeof x === "object" && safe(x.title) && !safe(x.name);
    const isItem = (x) => x && typeof x === "object" && safe(x.name) && safe(x.url);

    function sliceBetween(arr, startIncludes, endIncludes) {
      const startIdx = arr.findIndex(x => isHeader(x) && safe(x.title).toLowerCase().includes(startIncludes));
      if (startIdx < 0) return [];
      let endIdx = arr.length;
      if (endIncludes) {
        const ei = arr.findIndex((x, i) => i > startIdx && isHeader(x) && safe(x.title).toLowerCase().includes(endIncludes));
        if (ei >= 0) endIdx = ei;
      }
      return arr.slice(startIdx + 1, endIdx).filter(isItem);
    }

    let items = [];
    if (group === "study") items = sliceBetween(top, "study wise", "popular");
    else if (group === "popular") items = sliceBetween(top, "popular", null);
    else if (group === "state") items = sliceBetween(left, "state wise", "admit");
    else if (group === "admit-result") items = sliceBetween(left, "admit", null);
    else if (group === "admissions") items = sliceBetween(right, "admissions", "govt scheme");
    else if (group === "khabar") items = sliceBetween(right, "latest khabar", "study material");
    else if (group === "study-material") items = sliceBetween(right, "study material", "tools");

    // Filter Garbage
    items = items.filter(i => !isGarbageLink(i));

    gridEl.innerHTML = "";
    items.forEach((it) => {
      const a = document.createElement("a");
      a.className = "section-link";

      // ✅ FIX: State wise jobs → /state-jobs/{slug}/ (SEO-friendly static pages)
      let href = safe(it.url);
      if (group === "state") {
        // Extract state name from the item name or url
        // Item name example: "Delhi State Jobs", "Gujarat State Jobs"
        // URL example: /state/delhi/
        let extractedState = "";
        // Try from URL param first
        try {
          const urlObj = new URL(href, location.href);
          const sec = urlObj.searchParams.get("section") || "";
          if (sec) {
            // "Delhi State Jobs" → "Delhi", "Haryana All State Jobs" → "Haryana"
            extractedState = sec.replace(/\s+(all\s+)?state\s+jobs?/gi, '').replace(/\s+govt\s+jobs?/gi,'').trim();
          }
        } catch(_) {}
        // If not from URL, try from item name
        if (!extractedState) {
          const nameClean = safe(it.name).replace(/\s+(all\s+)?state\s+jobs?/gi,'').replace(/\s+govt\s+jobs?/gi,'').trim();
          extractedState = nameClean;
        }
        if (extractedState) {
          href = `/state-jobs/${extractedState.toLowerCase().replace(/ /g, '-')}/`;
        }
      }

      a.href = href;
      if (it.external) { a.target = "_blank"; a.rel = "noopener"; }
      a.innerHTML = `<div class="t">${safe(it.name)}</div>`;
      gridEl.appendChild(a);
    });

    const mainContainer = $("#main") || $("main") || document.body;
    let seoBox = document.getElementById("dynamic-seo-box");
    if (seoBox) seoBox.remove(); 

    let seoHTML = "";

    if (group === "study") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Government Exam Study Resources 2026 – Free Study Material, Syllabus, Mock Tests & Preparation Strategy</h2>
          <p>Preparing for a Sarkari Job in India requires more than just hard work — it requires the right strategy, authentic study material, structured revision plan, and consistent practice. The Study section of Top Sarkari Jobs is designed to be your complete preparation hub for all major Government Exams 2026 including UPSC, SSC, Railway, Banking, State PSC, Police, Defence, CUET, JEE, NEET and other competitive exams.</p>
          <p>Yahan par aapko milega free study material, official syllabus guidance, trusted government learning portals, previous year question papers, conceptual video lectures, and structured preparation roadmap — sab ek hi jagah par. This page is not just about downloading PDFs. It is about building strong conceptual clarity, analytical ability and exam confidence.</p>
          
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Why Structured Study Resources Matter</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">Government exams in India are highly competitive. Lakhs of candidates apply every year for limited vacancies. Random preparation se selection mushkil hota hai. Structured preparation se success possible hoti hai. Most exams test:</p>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>Conceptual clarity & Analytical reasoning</li>
                <li>Current affairs awareness</li>
                <li>Time management & Accuracy under pressure</li>
              </ul>
            </div>
            <div class="seo-card">
              <h3>Start with NCERT – Foundation</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">Almost every major competitive exam is linked to NCERT concepts (History, Geography, Polity, Economics, General Science). For UPSC and State PSC, Class 6–12 is mandatory.</p>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in/textbook.php</a></p>
            </div>
            <div class="seo-card">
              <h3>SWAYAM & NPTEL – Online Courses</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">SWAYAM offers free courses by IIT/IIM professors for Gen Studies, Economics, etc.</p>
              <p style="font-size: 13px; margin-bottom: 8px; font-weight: 600;">👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">NPTEL offers technical & analytical lectures (Aptitude, Reasoning, Engineering).</p>
              <p style="font-size: 13px; font-weight: 600;">👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nptel.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>National Digital Library (NDLI)</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">Access academic books, research material, and previous year papers.</p>
              <p style="font-size: 13px; margin-bottom: 8px; font-weight: 600;">👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ndl.iitkgp.ac.in</a></p>
            </div>
          </div>
          <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line);">
            <h3 style="font-size: 16px; font-weight: 900; margin-bottom: 8px;">Smart Study Plan & Syllabus Strategy</h3>
            <p style="font-size: 14px; color: var(--muted); line-height: 1.6; margin-bottom: 8px;">Always download the official syllabus (e.g., from <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">upsc.gov.in</a> or <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a>). Avoid studying from too many sources, ignoring past papers, and following unverified PDFs.</p>
            <ul style="list-style-type: decimal; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 14px;">
              <li>Complete NCERT (Foundation)</li>
              <li>Download official syllabus & create timetable</li>
              <li>Take SWAYAM/NPTEL lectures</li>
              <li>Solve previous year question papers & weekly mock tests</li>
            </ul>
            <p style="font-size: 14px; font-weight: 700; color: #0ea5e9; margin-top: 10px;">Preparation smart honi chahiye, sirf hard work se selection nahi hota.</p>
          </div>
        </section>`;
    } else if (group === "popular") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Popular Government Exams 2026 – Most Applied Sarkari Jobs in India</h2>
          <p>Every year, millions of aspirants apply for popular government exams in India. These exams offer job security, stable salary, pension benefits, and long-term career growth. The Popular section of Top Sarkari Jobs highlights the most searched, most competitive and high-demand Sarkari exams in India for 2026.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>UPSC Civil Services Examination</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">Recruits for IAS, IPS, IFS and other Group A services. Prep: NCERT foundation, daily newspaper, analytical writing, mock tests.</p>
              <p style="font-size: 13px; margin-bottom: 4px; font-weight: 600;">Official: 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">upsc.gov.in</a></p>
            </div>
            <div class="seo-card">
              <h3>NTA Conducted Exams</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">NTA conducts CUET (UG), JEE Main, NEET UG, UGC NET, CSIR NET.</p>
              <p style="font-size: 13px; margin-bottom: 4px; font-weight: 600;">Official: 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>SSC & Railway Exams</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">SSC (CGL, CHSL, MTS) and RRB (NTPC, Group D, ALP) require quantitative aptitude, english, general awareness, speed & accuracy.</p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NCERT Books:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in/textbook.php</a></p>
            </div>
            <div class="seo-card">
              <h3>Banking Exams (IBPS / SBI / RBI)</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">Popular for urban postings and structured promotions. Requires strong quantitative aptitude and reasoning.</p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>Concept lectures:</strong> 👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nptel.ac.in</a></p>
            </div>
          </div>
        </section>`;
    } else if (group === "state") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>State Wise Sarkari Jobs 2026 – State PSC, Police & Local Recruitment Updates</h2>
          <p>India has 28 states and each state conducts its own recruitment for administrative, police, teaching and technical posts. This section helps candidates explore State PSC Notifications, State Police Recruitment, State Teaching Jobs, and State Level Group B & C Vacancies.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Why State Jobs Are Important</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>Local posting & Language advantage</li>
                <li>Stable career & Regional growth</li>
              </ul>
            </div>
            <div class="seo-card">
              <h3>Official Government Portals</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>Civil Services:</strong> 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">upsc.gov.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>National Exams:</strong> 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a></p>
              <p style="font-size: 13px; color: var(--muted);">Always verify notifications from official sources.</p>
            </div>
            <div class="seo-card">
              <h3>State Exam Preparation Strategy</h3>
              <p style="font-size: 13px; margin-bottom: 4px;">1. NCERT foundation: 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;">2. State specific history: 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ndl.iitkgp.ac.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;">3. Concept lectures: 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
            </div>
            <div class="seo-card">
              <h3>Subjects Common in State Exams</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>State History & Geography</li>
                <li>Indian Polity & Current Affairs</li>
              </ul>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">Preparation must combine local + national knowledge.</p>
            </div>
          </div>
        </section>`;
    } else if (group === "admissions") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>University Admissions 2026 – Entrance Exams, Eligibility & Preparation Resources</h2>
          <p>This section covers national and university-level entrance examinations. Students searching for CUET 2026, JEE Main 2026, NEET UG 2026, UGC NET, or Central University Admissions will find verified and structured guidance here.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>National Testing Agency (NTA)</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">NTA conducts major national entrance exams. Candidates must track deadlines, download admit cards, and review correction notices.</p>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>Academic Preparation Resources</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NCERT:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in/textbook.php</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>SWAYAM:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NPTEL:</strong> 👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nptel.ac.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NDLI:</strong> 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ndl.iitkgp.ac.in</a></p>
            </div>
          </div>
          <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line);">
            <h3 style="font-size: 16px; font-weight: 900; margin-bottom: 8px;">Admission Preparation Strategy</h3>
            <p style="font-size: 14px; color: var(--muted);">Follow official syllabus, practice mock tests, revise fundamentals, and track official announcements. Avoid relying on unverified portals.</p>
          </div>
        </section>`;
    } else if (group === "admit-result") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Sarkari Admit Card & Result 2026 – Official Download Links & Verification Guide</h2>
          <p>This section provides verified links for Sarkari Result 2026, Government Exam Admit Cards, Scorecards, and Merit Lists.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Official Portals</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NTA:</strong> 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>UPSC:</strong> 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">upsc.gov.in</a></p>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">Always use official websites only.</p>
            </div>
            <div class="seo-card">
              <h3>Between Admit Card & Exam</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NCERT:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in/textbook.php</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>Concept courses:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>Advanced practice:</strong> 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ndl.iitkgp.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>After Result Declaration</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>Check cut-off</li>
                <li>Download scorecard</li>
                <li>Prepare for next stage</li>
              </ul>
            </div>
          </div>
        </section>`;
    } else if (group === "khabar") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Latest Government Exam News 2026 – Official Notifications & Updates</h2>
          <p>Stay updated with exam date changes, application extensions, correction windows, and result announcements.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Trusted Sources</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NTA Official:</strong> 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>UPSC Official:</strong> 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">upsc.gov.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>Educational portal:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
            </div>
            <div class="seo-card">
              <h3>Why News Section Matters</h3>
              <p style="font-size: 13px; color: var(--muted);">Timely information helps avoid missed deadlines. Never rely on rumors.</p>
            </div>
          </div>
        </section>`;
    } else if (group === "study-material") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Free Study Material for Government Exams – Download PDFs & Online Courses</h2>
          <p>This page is dedicated exclusively to preparation material.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Foundation & Online Learning</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NCERT Textbooks:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in/textbook.php</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>SWAYAM:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NPTEL:</strong> 👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nptel.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>Research & Reference Library</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>National Digital Library:</strong> 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ndl.iitkgp.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>Complete Preparation Ecosystem</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>Learn basics from NCERT</li>
                <li>Deepen understanding via SWAYAM</li>
                <li>Improve analytical skills through NPTEL</li>
                <li>Practice using NDLI materials</li>
                <li>Track official updates via <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">NTA</a> & <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">UPSC</a></li>
              </ul>
            </div>
          </div>
        </section>`;
    }

    if (seoHTML) {
      seoBox = document.createElement("div");
      seoBox.id = "dynamic-seo-box";
      seoBox.innerHTML = seoHTML;
      mainContainer.appendChild(seoBox);
    }
  }

  // Tools Page
  async function initToolsPage() {
    if (!isToolsPage) return;

    const categoriesView = $("#categories-view");
    const toolsView = $("#tools-view");
    const toolsGrid = $("#tools-grid");
    const toolsTitle = $("#tools-title span") || $("#tools-title");
    const backBtn = $("#back-button");
    const categoryButtons = $$(".category-button");

    if (!categoriesView || !toolsView || !toolsGrid || !categoryButtons.length) return;

    const fallbackData = {
      image: [
         { name: "Image Resizer", url: "https://imageresizer.com/", icon: "fa-solid fa-compress", external: true },
         { name: "Compress Image", url: "https://tinypng.com/", icon: "fa-solid fa-file-image", external: true },
         { name: "Passport Photo Maker", url: "https://www.cutout.pro/passport-photo-maker", icon: "fa-solid fa-id-card", external: true }
      ],
      pdf: [
         { name: "JPG to PDF", url: "https://www.ilovepdf.com/jpg_to_pdf", icon: "fa-solid fa-file-pdf", external: true },
         { name: "Compress PDF", url: "https://www.ilovepdf.com/compress_pdf", icon: "fa-solid fa-file-zipper", external: true },
         { name: "Merge PDF", url: "https://www.ilovepdf.com/merge_pdf", icon: "fa-solid fa-file-circle-plus", external: true }
      ],
      video: [
         { name: "Video Compressor", url: "https://www.freeconvert.com/video-compressor", icon: "fa-solid fa-video", external: true },
         { name: "MP4 to MP3", url: "https://cloudconvert.com/mp4-to-mp3", icon: "fa-solid fa-music", external: true }
      ]
    };

    let toolsData = fallbackData;
    try {
      const json = await getJSON("/tools.json");
      if (json && Object.keys(json).length > 0) toolsData = json;
    } catch (_) {}

    const showCategories = () => {
      toolsView.classList.add("hidden");
      categoriesView.classList.remove("hidden");
      if(history.pushState) history.pushState(null, null, location.pathname);
      window.scrollTo({ top: 0, behavior: "instant" });
    };

    const showTools = (categoryKey) => {
      const list = Array.isArray(toolsData[categoryKey]) ? toolsData[categoryKey] : [];
      const titleMap = { image: "Image Tools", pdf: "PDF Tools", video: "Video/Audio Tools" };
      if (toolsTitle) toolsTitle.textContent = titleMap[categoryKey] || "Tools";

      toolsGrid.innerHTML = "";
      if (!list.length) {
        toolsGrid.innerHTML = `<div class="col-span-full p-4 text-center text-gray-600">No tools found.</div>`;
      } else {
        list.forEach((t) => {
          const name = safe(t.name) || "Open Tool";
          const url = t.url || t.link || "";
          if (!url) return;
          const isExternal = t.external === true;
          const a = document.createElement("a");
          a.className = "p-4 rounded-lg bg-white border border-gray-200 hover:bg-blue-50 hover:border-blue-300 transition duration-300 flex items-start gap-3 text-left";
          a.href = isExternal ? normalizeUrl(url) : openInternal(url, name);
          if (isExternal) { a.target = "_blank"; a.rel = "noopener"; }

          const iconClass = safe(t.icon) || "fas fa-wand-magic-sparkles";
          a.innerHTML = `
            <div class="mt-0.5 text-xl text-blue-600"><i class="${iconClass}"></i></div>
            <div><div class="font-semibold text-gray-800">${name}</div><div class="text-sm text-gray-500 mt-1">Open tool</div></div>
          `;
          toolsGrid.appendChild(a);
        });
      }

      categoriesView.classList.add("hidden");
      toolsView.classList.remove("hidden");
      window.scrollTo({ top: 0, behavior: "instant" });
    };

    if (backBtn) backBtn.addEventListener("click", showCategories);

    categoryButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = safe(btn.getAttribute("data-category"));
        if (!key) return;
        showTools(key);
      });
    });

    const params = new URLSearchParams(location.search);
    const cat = params.get("cat");
    if (cat && toolsData[cat]) {
      showTools(cat);
    } else {
      showCategories();
    }
  }

  // CSC Services 
  const CSC_TABLE = "csc_service_requests";
  let cscSupabase = null;

  async function ensureSupabaseClient() {
    if (cscSupabase) return cscSupabase;

    if (!window.supabase) {
      await new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.src = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2";
        s.async = true;
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
      }).catch(() => null);
    }

    if (!window.supabase) return null;

    try {
      const r = await fetch("/config.json", { cache: "default" });
      if (!r.ok) return null;
      const config = await r.json();
      if (!config?.supabase?.url || !config?.supabase?.anonKey) return null;

      cscSupabase = window.supabase.createClient(config.supabase.url, config.supabase.anonKey);
      return cscSupabase;
    } catch (_) {
      return null;
    }
  }

  function initCscModal() {
    const modal = $("#cscModal");
    const overlay = $("#cscModalOverlay");
    const closeBtn = $("#cscModalClose");
    const closeBtn2 = $("#cscCloseBtn");
    const form = $("#cscRequestForm");

    if (!modal || !overlay || !closeBtn || !form) return;

    const serviceNameEl = $("#cscServiceName");
    let currentService = { name: "", url: "" };

    const close = () => {
      modal.hidden = true;
      overlay.hidden = true;
      document.body.style.overflow = "";
    };

    const open = (service) => {
      currentService = service || { name: "", url: "" };
      if (serviceNameEl) serviceNameEl.textContent = currentService.name || "Service";

      modal.hidden = false;
      overlay.hidden = false;
      document.body.style.overflow = "hidden";

      const first = $("input, textarea", form);
      if (first) setTimeout(() => first.focus(), 50);
    };

    window.__openCscModal = open;

    overlay.addEventListener("click", close);
    closeBtn.addEventListener("click", close);
    if (closeBtn2) closeBtn2.addEventListener("click", close);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal.hidden) close();
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const fullName = safe($("#cscFullName")?.value);
      const phone = safe($("#cscPhone")?.value);
      const state = safe($("#cscState")?.value);
      const msg = safe($("#cscMessage")?.value);

      if (!fullName || !phone || phone.length < 8) {
        alert("Please fill all fields correctly.");
        return;
      }

      const sb = await ensureSupabaseClient();
      if (!sb) {
        alert("Submission system is temporarily unavailable. Please try again later.");
        return;
      }

      const serviceText = [
        safe(currentService.name) ? safe(currentService.name) : "-",
        state ? `State: ${state}` : "",
        currentService.url ? `Link: ${normalizeUrl(currentService.url)}` : "",
        msg ? `Details: ${msg}` : "",
      ]
        .filter(Boolean)
        .join("\n");

      try {
        const { error } = await sb.from(CSC_TABLE).insert([
          {
            name: fullName,
            phone: phone,
            service: serviceText,
            created_at: new Date().toISOString(),
          },
        ]);

        if (error) {
          console.error("Supabase insert error:", error);
          alert("Failed to submit your request. Please try again.");
          return;
        }

        alert("Request submitted successfully. We will contact you soon.");
        form.reset();
        close();
      } catch (err) {
        console.error("Submit error:", err);
        alert("Could not submit your request. Please check your connection and try again.");
      }
    });
  }

  async function renderServicesPage() {
    if (page !== "govt-services.html") return;

    const list = $("#servicesList");
    if (!list) return;

    let data = null;
    try { data = await getJSON("/services.json"); } catch (_) {}

    const services = (data && (data.services || data)) || [];
    list.innerHTML = "";

    if (!Array.isArray(services) || !services.length) {
      list.innerHTML = `<div class="seo-block"><strong>No services found.</strong><p>Please check services.json.</p></div>`;
      return;
    }

    services.forEach((s) => {
      const name = safe(s.name || s.service).replace("ceck", "check");
      const url = s.url || s.link || "";
      if (!name) return;

      const a = document.createElement("a");
      a.className = "section-link csc-service-link";
      a.href = "#";
      a.setAttribute("role", "button");
      a.innerHTML = `
        <div class="t">${name}</div>
        <div class="d">Click to fill details & submit request</div>
      `;

      a.addEventListener("click", (e) => {
        e.preventDefault();
        if (typeof window.__openCscModal === "function") {
          window.__openCscModal({ name, url });
        }
      });

      list.appendChild(a);
    });
  }

  // ✅ GLOBAL LIVE SEARCH ENGINE (Works instantly on 1 letter!)
  async function initGlobalLiveSearch() {
    const inputs = [];
    
    // heroSearch handled by inline heroSearchInit() in index.html (richer UI)
    // Do NOT add it here to avoid double-binding.

    const homeInput = document.getElementById("siteSearchInput");
    if (homeInput) inputs.push({ input: homeInput, resultsId: "searchResults" });
    
    const sectionInput = document.getElementById("sectionSearchInput");
    if (sectionInput) inputs.push({ input: sectionInput, resultsId: "sectionSearchResults" });
    
    const mobileBottomInput = document.getElementById("mobileBottomSearchInput");
    if (mobileBottomInput) inputs.push({ input: mobileBottomInput, resultsId: "mobileBottomSearchResults" });

    if (!inputs.length) return;

    /* ── keyword category helper ── */
    const KW = {
      'Admit Card' : ['admit card','hall ticket','call letter'],
      'Answer Key' : ['answer key','answer sheet','objection'],
      'Result'     : ['result','merit list','cut off','cutoff','scorecard'],
      'Admission'  : ['admission','counselling','counseling']
    };
    function categoryOf(title) {
      const t = title.toLowerCase();
      for (const [cat, words] of Object.entries(KW))
        if (words.some(w => t.includes(w))) return cat;
      return 'Latest Job';
    }
    function slugify(t) {
      return t.toLowerCase().replace(/[^a-z0-9\s-]/g,'').replace(/[\s-]+/g,'-').slice(0,120).replace(/^-+|-+$/g,'');
    }
    function jobHref(j) {
      const slug = j.slug || slugify(j.title || '');
      if (!slug) return j.official_website_link || '#';
      /* FIX: No 'offline-' prefix — merged_sarkari_data.json jobs have no slug field,
         so slug is generated from title. Adding 'offline-' creates a mismatch with
         the title-derived slug used in matchBySlug(), causing wrong data on first load. */
      return '/jobs/' + slug + '/';
    }

    let searchData = [];
    /* PERF FIX: Complete_Jobs_Full_Data.json is now 5MB+ gzipped (30MB+
       raw) — fetching it eagerly on every page load tanked LCP/TBT
       site-wide. Load it lazily, only once a visitor actually touches a
       search box (focus/input), and memoize so it only fetches once. */
    let searchDataPromise = null;
    function loadSearchData() {
      if (searchDataPromise) return searchDataPromise;
      searchDataPromise = (async () => {
      try {
      /* ── ONLY these 4 authoritative JSON files are used for search ──
         jobs.json / tools.json / services.json are EXCLUDED intentionally.
         ─────────────────────────────────────────────────────────────── */
      const [cjData, daily] = await Promise.all([
        getJSON("/data/Complete_Jobs_Full_Data.json").catch(() => null),
        getJSON("dailyupdates.json").catch(() => null),
      ]);
      const complete = cjData;
      // sarkari_data.jobs contains SR_Latest_Jobs, SR_Result, SR_Admit_Card etc.
      const merged = cjData ? { jobs: (cjData.sarkari_data || {}).jobs || [] } : null;
      // state_jobs.sections contains all state jobs
      const stateJobs = cjData ? { sections: (cjData.state_jobs || {}).sections || [] } : null;

      const push = (name, url, src) => {
        if(!name || !url) return;
        if (isGarbageLink({name})) return;
        // Block tools / services / category nav links
        if (!url || url === '#') return;
        if (/\/(tools|govt-services|category|about|contact|result\.html|admit-card\.html)\b/i.test(url)) return;
        searchData.push({ name: name.trim(), url: url.trim(), src });
      };

      /* 1. merged_sarkari_data.json — jobs[] array */
      if (merged && Array.isArray(merged.jobs)) {
        merged.jobs.forEach(j => {
          if (!j.title) return;
          const cat = (j.apply_mode||'').toLowerCase() === 'offline' ? 'Offline Form' : categoryOf(j.title);
          push(j.title, jobHref(j), cat);
        });
      }

      /* 2. dailyupdates.json */
      if (daily) {
        const arr = Array.isArray(daily) ? daily : (Array.isArray(daily.sections) ? daily.sections : []);
        arr.forEach(sec => {
          (sec.items || []).forEach(i => {
            const itemUrl = i.url || i.link || '';
            // Only push job detail URLs (job.html) or valid sarkari links
            if (!itemUrl || itemUrl === '#') return;
            push(i.name || i.title, itemUrl, sec.title || 'Update');
          });
        });
      }

      /* 3. Complete_Jobs_Full_Data.json — freejobalert_categories */
      if (complete && complete.freejobalert_categories) {
        const cats = complete.freejobalert_categories;
        Object.keys(cats).forEach(k => {
          if (!Array.isArray(cats[k])) return;
          cats[k].forEach(i => {
            const bd = i.basic_details || {};
            const title = bd.job_title || bd.post_name || i.title || i.name || '';
            if (!title) return;
            const slug = i.slug || slugify(title);
            const href = slug ? '/jobs/' + slug + '/' : '#';
            push(title, href, k.replace(/_/g,' '));
          });
        });
      }

      /* 4. state-jobs-data.json — structure: { sections: [{state, title, items:[{name,url,...}]}] } */
      if (stateJobs && Array.isArray(stateJobs.sections)) {
        stateJobs.sections.forEach(sec => {
          const stateName = sec.state || sec.title || 'State Jobs';
          (sec.items || []).forEach(item => {
            const title = item.name || item.title || '';
            if (!title) return;
            // Build internal job.html link using slug
            const slug = item.slug || slugify(title);
            const href = slug
              ? '/jobs/' + slug + '/'
              : (item.url || '#');
            push(title, href, stateName + ' Jobs');
          });
        });
      }
      } catch (e) {}
      })();
      return searchDataPromise;
    }

    inputs.forEach(({ input, resultsId }) => {
      const resultsWrap = document.getElementById(resultsId);
      if (!resultsWrap) return;

      const performSearch = async () => {
        const query = input.value.toLowerCase().trim();
        if (query.length < 1) {
          resultsWrap.innerHTML = "";
          resultsWrap.style.display = "none";
          return;
        }

        await loadSearchData();

        const tokens = query.split(/\s+/).filter(t => t.length);
        const matches = searchData.filter(item => {
          const hay = (item.name + " " + item.src).toLowerCase();
          return tokens.every(t => hay.includes(t));
        }).slice(0, 10);

        resultsWrap.innerHTML = "";
        /* use .suggest-item for #searchSuggest, .search-result-item for others */
        const isSuggest = resultsWrap.id === "searchSuggest";
        if (matches.length > 0) {
          resultsWrap.style.display = "block";
          if (isSuggest) resultsWrap.classList.add("open");
          matches.forEach(m => {
            let href = normalizeUrl(m.url);
            const isExternal = href.startsWith("http") && !href.includes(location.hostname);
            const a = document.createElement("a");
            a.className = isSuggest ? "suggest-item" : "search-result-item";
            a.href = href;
            if (isExternal) { a.target = "_blank"; a.rel = "noopener"; }
            if (isSuggest) {
              a.innerHTML = `<i class="fa-solid fa-circle-dot" style="color:var(--blue);min-width:16px;font-size:.8rem;"></i><span style="flex:1;min-width:0;"><span style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${m.name}</span><span style="font-size:.7rem;color:var(--muted);font-weight:400;">${m.src}</span></span>`;
            } else {
              a.innerHTML = `<div class="result-name">${m.name}</div><div class="result-meta">${m.src}</div>`;
            }
            resultsWrap.appendChild(a);
          });
        } else {
          resultsWrap.style.display = "block";
          if (isSuggest) resultsWrap.classList.add("open");
          resultsWrap.innerHTML = isSuggest
            ? `<div class="suggest-item" style="color:var(--muted);justify-content:center;">No results found. Try SSC, Railway, Bank, Admit Card…</div>`
            : `<div class="search-no-results">No matches found.</div>`;
        }
      };

      input.addEventListener("input", performSearch);
      input.addEventListener("focus", () => { loadSearchData(); if(input.value.length >= 1) resultsWrap.style.display="block"; });
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); performSearch(); }
      });

      // ISSUE-008: wire the visible Search button so clicking it actually
      // runs the search (was previously inert).
      const btnId = input.id === "siteSearchInput" ? "siteSearchBtn"
                  : input.id === "sectionSearchInput" ? "sectionSearchBtn"
                  : input.id === "heroSearch" ? "heroSearchBtn"
                  : input.id === "mobileBottomSearchInput" ? "mobileBottomSearchBtn"
                  : null;
      const btn = btnId ? document.getElementById(btnId) : null;
      if (btn && !btn.dataset.qaBound) {
        btn.dataset.qaBound = "1";
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          if (!input.value.trim()) { input.focus(); return; }
          performSearch();
        });
      }

      document.addEventListener("click", (e) => {
        if (btn && btn.contains(e.target)) return;
        if (!input.contains(e.target) && !resultsWrap.contains(e.target)) {
          resultsWrap.style.display = "none";
          resultsWrap.classList.remove("open");
        }
      });
      input.addEventListener("keydown", (e) => {
        if (e.key === "Escape") { resultsWrap.style.display = "none"; resultsWrap.classList.remove("open"); resultsWrap.innerHTML = ""; }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    installGlobalRedirectGate();

    // ✅ Remove home-quicklinks-wrap from DOM immediately (all pages)
    const qlWrap = document.getElementById("home-quicklinks-wrap");
    if (qlWrap) qlWrap.remove();
    // Also remove any injected home-links or mobile-nav-grid
    ["home-links", "mobile-nav-grid", "mobile-bottom-search", "home-quicklinks-style"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.remove();
    });

    buildMobileMenu();   // NOTE: runs again after header inject — safe, idempotent
    safeHideOldSearchBars();

    // Expose init hook for pages that inject header before script.js loads
    window.__TSJ_INIT_HEADER = function() {
      buildMobileMenu();
      initOffcanvas();
      initDropdowns();
    };

    await injectHeaderFooter();  // ← buildMobileMenu() also called inside here after DOM ready
    await loadHeaderLinks();
    initOffcanvas();   // called again here as safety fallback
    initDropdowns();   // called again here as safety fallback
    initFAQ();

    if (page === "index.html" || page === "") {
      // ── SPEED FIX: render sections WITHOUT waiting for header/footer inject ──
      // renderHomepageSections runs in parallel with injectHeaderFooter
      renderHomepageSections();
      // Daily updates: defer to idle time (below fold, not critical)
      var deferDailyUpdates = function() {
        renderDailyUpdatesSections();
      };
      if ('requestIdleCallback' in window) {
        requestIdleCallback(deferDailyUpdates, { timeout: 1500 });
      } else {
        setTimeout(deferDailyUpdates, 1500);
      }
      removeHomeMainPageCtaLinks();
    }
    
    // renderHomeQuickLinks() — PERMANENTLY DISABLED (removed from all pages)
    await initCategoryPage();
    await initToolsPage();
    
    if (page === "govt-services.html") {
      ensureSupabaseClient().catch(() => {});
    }
    initCscModal();
    await renderServicesPage();
    
    await initGlobalLiveSearch();
  });
})();
