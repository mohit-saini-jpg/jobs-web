(() => {
  "use strict";

  // Guard: prevents double-init (double listeners = stuck menu)
  if (window.__TSJ_BOOT__) return;
  window.__TSJ_BOOT__ = true;

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const safe = (v) => (v ?? "").toString().trim();

  const PAGE = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  function normalizeUrl(raw) {
    const url = safe(raw);
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    if (url.startsWith("//")) return "https:" + url;
    if (url.startsWith("www.")) return "https://" + url;
    // internal pages / relative paths
    if (url.startsWith("/") || url.endsWith(".html") || url.includes("view.html")) return url;
    // external but missing scheme
    return "https://" + url;
  }

  function toView(url, name) {
    return `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`;
  }

  function debounce(fn, ms = 160) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  // ----------------------------
  // 1) FIX: Mobile side-menu stuck
  // Works with your existing IDs: #hamburger, #side-menu, #close-menu, #overlay
  // ----------------------------
  function initMobileMenu() {
    const hamburger = $("#hamburger");
    const sideMenu = $("#side-menu");
    const closeBtn = $("#close-menu");
    const overlay = $("#overlay");

    if (!hamburger || !sideMenu || !closeBtn || !overlay) return;

    const unlockScroll = () => {
      document.body.style.overflow = "";
      document.documentElement.style.overflow = "";
    };

    const closeMenu = () => {
      sideMenu.classList.remove("open");
      overlay.classList.remove("show");
      sideMenu.setAttribute("aria-hidden", "true");
      hamburger.setAttribute("aria-expanded", "false");
      unlockScroll();
    };

    const openMenu = () => {
      sideMenu.classList.add("open");
      overlay.classList.add("show");
      sideMenu.setAttribute("aria-hidden", "false");
      hamburger.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
      document.documentElement.style.overflow = "hidden";
    };

    // Reset handlers to prevent duplicates
    hamburger.onclick = openMenu;
    closeBtn.onclick = closeMenu;
    overlay.onclick = closeMenu;

    // Close when clicking any link inside
    sideMenu.addEventListener("click", (e) => {
      const a = e.target.closest("a");
      if (a) closeMenu();
    });

    // ESC closes
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeMenu();
    });

    // On resize to desktop, force close
    window.addEventListener("resize", () => {
      if (window.innerWidth > 980) closeMenu();
    });

    // Safety: if overlay visible but menu not open, fix state
    setInterval(() => {
      const overlayOn = overlay.classList.contains("show");
      const menuOn = sideMenu.classList.contains("open");
      if (overlayOn && !menuOn) closeMenu();
    }, 800);

    window.__TSJ_CLOSE_MENU__ = closeMenu;
  }

  // ----------------------------
  // 2) FIX: Desktop dropdown close behavior (prevents stuck dropdown overlays)
  // Works with your existing ".dropdown" markup
  // ----------------------------
  function initDesktopDropdowns() {
    const dropdowns = $$(".dropdown");
    if (!dropdowns.length) return;

    const closeAll = () => {
      dropdowns.forEach((dd) => dd.classList.remove("open"));
    };

    dropdowns.forEach((dd) => {
      const btn = dd.querySelector("button");
      if (!btn) return;

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const wasOpen = dd.classList.contains("open");
        closeAll();
        if (!wasOpen) dd.classList.add("open");
      });
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".dropdown")) closeAll();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeAll();
    });

    window.addEventListener("scroll", closeAll, { passive: true });
  }

  // ----------------------------
  // 3) FIX: Make sure Jobs / Admissions / More exist on ALL pages
  // If some pages have an older header missing dropdown sections, we inject them.
  // ----------------------------
  const NAV_GROUPS = [
    {
      label: "Jobs",
      items: [
        { label: "Study-wise Jobs", href: "category.html?group=study" },
        { label: "Popular Job Categories", href: "category.html?group=popular" },
        { label: "State-wise Jobs", href: "category.html?group=state" },
      ],
    },
    {
      label: "Admissions",
      items: [
        { label: "Admissions", href: "category.html?group=admissions" },
        { label: "Admit Card / Result / Answer Key / Syllabus", href: "category.html?group=admit-result" },
      ],
    },
    {
      label: "More",
      items: [
        { label: "Latest Khabar", href: "category.html?group=khabar" },
        { label: "Study Material & Top Courses", href: "category.html?group=study-material" },
      ],
    },
  ];

  function ensureNavConsistency() {
    // Desktop nav UL (your pages use: nav.desktop-nav ul)
    const desktopUl = $(".desktop-nav ul");
    if (desktopUl && !desktopUl.querySelector('[data-tsj-nav="groups"]')) {
      // Insert groups BEFORE CSC/Tools/Helpdesk/Search if they exist; else append
      const marker =
        desktopUl.querySelector('a[href="govt-services.html"]')?.closest("li") ||
        desktopUl.querySelector('a[href="tools.html"]')?.closest("li") ||
        null;

      const frag = document.createDocumentFragment();

      NAV_GROUPS.forEach((g) => {
        const li = document.createElement("li");
        li.className = "dropdown";
        li.setAttribute("data-tsj-nav", "groups");

        li.innerHTML = `
          <button type="button">${g.label} <i class="fa-solid fa-chevron-down"></i></button>
          <ul class="dropdown-menu"></ul>
        `;

        const menu = li.querySelector(".dropdown-menu");
        g.items.forEach((it) => {
          const itemLi = document.createElement("li");
          itemLi.innerHTML = `<a href="${it.href}">${it.label}</a>`;
          menu.appendChild(itemLi);
        });

        frag.appendChild(li);
      });

      if (marker) desktopUl.insertBefore(frag, marker);
      else desktopUl.appendChild(frag);
    }

    // Mobile side-menu UL (your pages use: #side-menu nav ul)
    const mobileUl = $("#side-menu nav ul");
    if (mobileUl) {
      const hasStudy = !!mobileUl.querySelector('a[href*="category.html?group=study"]');
      if (!hasStudy) {
        // Insert after Home
        const homeLi = mobileUl.querySelector('a[href="index.html"]')?.closest("li");

        const frag = document.createDocumentFragment();
        NAV_GROUPS.flatMap((g) => g.items).forEach((it) => {
          const li = document.createElement("li");
          li.innerHTML = `<a href="${it.href}">${it.label}</a>`;
          frag.appendChild(li);
        });

        if (homeLi && homeLi.nextSibling) mobileUl.insertBefore(frag, homeLi.nextSibling);
        else mobileUl.appendChild(frag);
      }
    }
  }

  // ----------------------------
  // 4) Restore content on HOME (this is why your site looks empty)
  // - #home-cards populated from jobs.json top_jobs
  // - #dynamic-sections populated from dynamic-sections.json
  // ----------------------------
  async function fetchJson(path) {
    try {
      const r = await fetch(path, { cache: "no-store" });
      if (!r.ok) return null;
      return await r.json();
    } catch {
      return null;
    }
  }

  function renderHomeCards(jobsJson) {
    const mount = $("#home-cards");
    if (!mount) return;

    const cards = Array.isArray(jobsJson?.top_jobs) ? jobsJson.top_jobs : [];
    if (!cards.length) return;

    mount.innerHTML = cards
      .filter((x) => x && !x.title)
      .slice(0, 18)
      .map((it) => {
        const name = safe(it.name);
        const url = normalizeUrl(it.url || it.link || "");
        if (!name || !url) return "";
        const href = it.external ? url : toView(url, name);
        const extra = it.external ? ` target="_blank" rel="noopener"` : "";
        return `<a class="home-card" href="${href}"${extra}>${name}</a>`;
      })
      .join("");
  }

  function iconFor(title) {
    const t = safe(title).toLowerCase();
    if (t.includes("latest")) return "fa-briefcase";
    if (t.includes("upcoming")) return "fa-clock";
    if (t.includes("admit")) return "fa-id-card";
    if (t.includes("result")) return "fa-square-poll-vertical";
    return "fa-link";
  }
  function colorFor(title) {
    const t = safe(title).toLowerCase();
    if (t.includes("latest")) return "#3b82f6";
    if (t.includes("upcoming")) return "#f59e0b";
    if (t.includes("admit")) return "#10b981";
    if (t.includes("result")) return "#8b5cf6";
    return "#0ea5e9";
  }

  function renderDynamicSections(dynamicJson) {
    const mount = $("#dynamic-sections");
    if (!mount) return;

    const sections = Array.isArray(dynamicJson?.sections) ? dynamicJson.sections : [];
    if (!sections.length) return;

    // Clear ONLY this container (do not touch other page content)
    mount.innerHTML = "";

    // Use your four big sections if present
    const wanted = [
      "Latest Jobs",
      "Upcoming Jobs",
      "Admit Cards & Exams Date",
      "Latest Results",
    ];

    const picked = [];
    wanted.forEach((w) => {
      const found = sections.find((s) => safe(s.title).toLowerCase() === w.toLowerCase());
      if (found) picked.push(found);
    });

    const finalList = picked.length ? picked : sections.slice(0, 4);

    finalList.forEach((sec) => {
      const title = safe(sec.title);
      const items = Array.isArray(sec.items) ? sec.items : [];
      const col = colorFor(title);
      const ic = iconFor(title);

      const card = document.createElement("article");
      card.className = "section-card";
      card.innerHTML = `
        <div class="section-head" style="background:${col}">
          <div class="left"><i class="fa-solid ${ic}"></i><span>${title}</span></div>
        </div>
        <div class="section-body">
          <div class="section-list"></div>
        </div>
      `;

      const list = card.querySelector(".section-list");
      items.slice(0, 15).forEach((it) => {
        const name = safe(it.name);
        const url = normalizeUrl(it.url || it.link || "");
        if (!name || !url) return;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = it.external ? url : toView(url, name);
        if (it.external) {
          a.target = "_blank";
          a.rel = "noopener";
        }
        a.innerHTML = `<div class="t">${name}</div><div class="d">${it.external ? "Open official link" : "Open"}</div>`;
        list.appendChild(a);
      });

      mount.appendChild(card);
    });
  }

  // ----------------------------
  // 5) Search: keep your existing search UI working
  // (#search-input, #search-results)
  // ----------------------------
  function initSearchIndex(jobsJson, dynamicJson) {
    const input = $("#search-input");
    const results = $("#search-results");
    if (!input || !results) return;

    const pool = [];

    // dynamic sections items
    (dynamicJson?.sections || []).forEach((sec) => {
      (sec.items || []).forEach((it) => {
        const title = safe(it.name);
        const url = normalizeUrl(it.url || it.link || "");
        if (!title || !url) return;
        pool.push({
          title,
          meta: safe(sec.title) || "Updates",
          href: it.external ? url : toView(url, title),
          external: !!it.external,
        });
      });
    });

    // job categories
    const jobLists = [
      ...(jobsJson?.left_jobs || []),
      ...(jobsJson?.right_jobs || []),
      ...(jobsJson?.top_jobs || []),
    ];
    jobLists.forEach((it) => {
      if (it?.title) return;
      const title = safe(it.name);
      const url = normalizeUrl(it.url || it.link || "");
      if (!title || !url) return;
      pool.push({
        title,
        meta: "Job Categories",
        href: it.external ? url : toView(url, title),
        external: !!it.external,
      });
    });

    const render = (q) => {
      const query = safe(q).toLowerCase();
      if (!query) {
        results.innerHTML = "";
        results.style.display = "none";
        return;
      }

      const matches = pool
        .filter((x) => x.title.toLowerCase().includes(query) || x.meta.toLowerCase().includes(query))
        .slice(0, 25);

      if (!matches.length) {
        results.innerHTML = `<div class="result-item"><div><div class="result-title">No results found</div><div class="result-meta">Try SSC, Railway, Police, Admit Card, Result, State name</div></div></div>`;
        results.style.display = "block";
        return;
      }

      const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const re = new RegExp(`(${esc(query)})`, "ig");

      results.innerHTML = matches
        .map((m) => {
          const title = safe(m.title).replace(re, "<mark>$1</mark>");
          const extra = m.external ? ` target="_blank" rel="noopener"` : "";
          return `
            <a class="result-item" href="${m.href}"${extra}>
              <div>
                <div class="result-title">${title}</div>
                <div class="result-meta">${safe(m.meta)}</div>
              </div>
              <div class="result-meta">${m.external ? "↗" : "→"}</div>
            </a>
          `;
        })
        .join("");

      results.style.display = "block";
    };

    input.addEventListener("input", debounce((e) => render(e.target.value), 140));

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".search-section")) {
        results.style.display = "none";
      }
    });
  }

  // ----------------------------
  // 6) Category page: restore missing grids (blue boxes / links)
  // (#category-grid, #category-title, #category-description)
  // ----------------------------
  function groupConfig(group) {
    const g = safe(group).toLowerCase();

    const map = {
      study: {
        title: "Study-wise Jobs",
        desc: "Find government jobs by education level (8th, 10th, 12th, ITI, Diploma, Graduation and more).",
        keys: ["left_jobs", "right_jobs"], // these already contain study-like categories in your data
      },
      popular: {
        title: "Popular Job Categories",
        desc: "Browse popular government job categories like SSC, Railway, Police, Banking, Teaching and more.",
        keys: ["left_jobs", "right_jobs"],
      },
      state: {
        title: "State-wise Jobs",
        desc: "Explore government jobs by Indian states and region-wise recruitment.",
        keys: ["left_jobs", "right_jobs"],
      },
      admissions: {
        title: "Admissions",
        desc: "Admissions, counseling updates, application forms and important university/board notices.",
        keys: ["left_jobs", "right_jobs"],
      },
      "admit-result": {
        title: "Admit Card / Result / Answer Key / Syllabus",
        desc: "Direct links for admit cards, results, answer keys and syllabus updates across exams.",
        keys: ["left_jobs", "right_jobs"],
      },
      khabar: {
        title: "Latest Khabar",
        desc: "Important updates, news and notices related to government recruitment and exams.",
        keys: ["left_jobs", "right_jobs"],
      },
      "study-material": {
        title: "Study Material & Top Courses",
        desc: "Useful learning resources and courses for exam preparation.",
        keys: ["left_jobs", "right_jobs"],
      },
    };

    return map[g] || map.study;
  }

  function renderCategoryPage(jobsJson) {
    if (PAGE !== "category.html") return;

    const grid = $("#category-grid");
    const titleEl = $("#category-title");
    const descEl = $("#category-description");
    if (!grid) return;

    const params = new URLSearchParams(location.search);
    const group = params.get("group") || "study";
    const cfg = groupConfig(group);

    if (titleEl) titleEl.textContent = cfg.title;
    if (descEl) descEl.textContent = cfg.desc;

    const items = [];
    (cfg.keys || []).forEach((k) => {
      (jobsJson?.[k] || []).forEach((it) => {
        if (it?.title) return;
        const name = safe(it.name);
        const url = normalizeUrl(it.url || it.link || "");
        if (!name || !url) return;
        items.push({
          name,
          href: it.external ? url : toView(url, name),
          external: !!it.external,
        });
      });
    });

    // If jobs.json is structured differently, fallback to any array found
    if (!items.length) {
      Object.keys(jobsJson || {}).forEach((k) => {
        if (!Array.isArray(jobsJson[k])) return;
        jobsJson[k].forEach((it) => {
          if (it?.title) return;
          const name = safe(it.name);
          const url = normalizeUrl(it.url || it.link || "");
          if (!name || !url) return;
          items.push({
            name,
            href: it.external ? url : toView(url, name),
            external: !!it.external,
          });
        });
      });
    }

    grid.innerHTML = items
      .slice(0, 90)
      .map((x) => {
        const extra = x.external ? ` target="_blank" rel="noopener"` : "";
        return `<a class="job-btn" href="${x.href}"${extra}>${x.name}</a>`;
      })
      .join("");
  }

  // ----------------------------
  // 7) CSC Services page: fix non-working links + restore list from services.json
  // Accepts any container id: #servicesList OR #services-grid
  // ----------------------------
  async function renderServicesPage() {
    if (PAGE !== "govt-services.html") return;

    const list = $("#servicesList") || $("#services-grid");
    if (!list) return;

    const data = await fetchJson("services.json");
    const services = Array.isArray(data?.services) ? data.services : (Array.isArray(data) ? data : []);

    if (!services.length) {
      list.innerHTML = `<div class="section-link"><div class="t">No services found</div><div class="d">Check services.json format</div></div>`;
      return;
    }

    list.innerHTML = services
      .map((s) => {
        const name = safe(s.name || s.service);
        const url = normalizeUrl(s.url || s.link || "");
        if (!name || !url) return "";
        return `
          <a class="section-link" href="${url}" target="_blank" rel="noopener">
            <div class="t">${name}</div>
            <div class="d">Open service link</div>
          </a>
        `;
      })
      .join("");
  }

  // ----------------------------
  // 8) SEO blocks:
  // - home: #seo-content (already in your index.html)
  // - other pages: adds a small brief block only if missing
  // ----------------------------
  function ensurePageBrief() {
    const main = $("main");
    if (!main) return;

    // If a page already has a #seo-content section (home), keep it.
    if ($("#seo-content")) return;

    // If a page already has any .seo-content or .seo-block, don't spam.
    if ($(".seo-content") || $(".seo-block")) return;

    const map = {
      "result.html": {
        h: "Latest Sarkari Results",
        p: "Check scorecards, merit lists, cutoffs and official PDFs. Always verify roll number and DOB on the official portal.",
      },
      "govt-services.html": {
        h: "CSC Services & Government Schemes",
        p: "Use trusted service links for documents and schemes. Verify requirements and charges on the official portal before submitting.",
      },
      "tools.html": {
        h: "Helpful Tools for Applicants",
        p: "Use quick tools to prepare documents for online forms. Keep PDFs clear and images readable before uploading.",
      },
      "search.html": {
        h: "Search Jobs, Results & Admit Cards",
        p: "Search using keywords like SSC, Railway, Police, Admit Card, Result, Board name or State name.",
      },
      "category.html": {
        h: "Browse Categories",
        p: "Use category pages to find relevant links faster. Always confirm eligibility, dates and official notices before applying.",
      },
    };

    const meta = map[PAGE];
    if (!meta) return;

    const sec = document.createElement("section");
    sec.className = "seo-content";
    sec.innerHTML = `<h2>${meta.h}</h2><p>${meta.p}</p>`;
    main.appendChild(sec);
  }

  // ----------------------------
  // BOOT: fetch required JSON once, then render per page
  // ----------------------------
  document.addEventListener("DOMContentLoaded", async () => {
    // 1) menu + dropdown fixes (safe for all pages)
    initMobileMenu();
    ensureNavConsistency();
    initDesktopDropdowns();

    // 2) load JSON that powers your content
    const jobsJson = await fetchJson("jobs.json");
    const dynamicJson =
      (PAGE === "index.html" || PAGE === "") ? await fetchJson("dynamic-sections.json") : null;

    // 3) restore content where needed
    if ((PAGE === "index.html" || PAGE === "") && jobsJson) {
      renderHomeCards(jobsJson);
      if (dynamicJson) renderDynamicSections(dynamicJson);
      if (dynamicJson) initSearchIndex(jobsJson, dynamicJson);
    }

    if (PAGE === "category.html" && jobsJson) {
      renderCategoryPage(jobsJson);
    }

    await renderServicesPage();
    ensurePageBrief();
  });
})();
/* Safety patch: overlay must never block clicks unless visible */
#overlay { pointer-events: none; }
#overlay.show { pointer-events: auto; }

/* Ensure side-menu stacks above overlay correctly */
#side-menu { z-index: 2000; }
