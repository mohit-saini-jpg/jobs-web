(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const PAGE = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  // Prevent double-boot (double listeners = stuck menus)
  if (window.__TSJ_BOOTED__) return;
  window.__TSJ_BOOTED__ = true;

  const safe = (v) => (v ?? "").toString().trim();

  function normalizeUrl(raw) {
    const url = safe(raw);
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    if (url.startsWith("//")) return "https:" + url;
    if (url.startsWith("www.")) return "https://" + url;
    if (url.startsWith("/") || url.endsWith(".html")) return url;
    return "https://" + url;
  }

  function debounce(fn, ms = 140) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  // -----------------------
  // NAV: ensure Jobs/Admissions/More show on ALL pages
  // -----------------------
  const NAV_GROUPS = [
    {
      label: "Jobs",
      items: [
        { label: "Study wise jobs", href: "category.html?group=study" },
        { label: "Popular job categories", href: "category.html?group=popular" },
        { label: "State wise jobs", href: "category.html?group=state" },
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

  function ensureHeaderStructure() {
    // If header exists, do NOT replace it. Only add missing containers.
    const header = $(".site-header") || $("header");
    if (!header) return;

    // Desktop nav container
    let desktopNav = $("#desktopNav");
    if (!desktopNav) {
      // Try to find a nav that already contains Home/Results etc.
      desktopNav = header.querySelector("nav");
      if (desktopNav) desktopNav.id = "desktopNav";
    }

    // Mobile menu button
    if (!$("#menuBtn")) {
      // If user has no hamburger, add in header-actions area
      let actions = header.querySelector(".header-actions");
      if (!actions) {
        actions = document.createElement("div");
        actions.className = "header-actions";
        header.appendChild(actions);
      }
      actions.insertAdjacentHTML(
        "beforeend",
        `
          <button id="menuBtn" class="icon-btn" type="button" aria-label="Open menu" aria-controls="mobileMenu" aria-expanded="false">
            <i class="fa-solid fa-bars"></i>
          </button>
        `
      );
    }

    // Overlay and offcanvas (only if missing)
    if (!$("#menuOverlay")) {
      const overlay = document.createElement("div");
      overlay.id = "menuOverlay";
      overlay.className = "overlay";
      overlay.hidden = true;
      document.body.appendChild(overlay);
    }

    if (!$("#mobileMenu")) {
      const menu = document.createElement("aside");
      menu.id = "mobileMenu";
      menu.className = "offcanvas";
      menu.hidden = true;
      menu.innerHTML = `
        <div class="offcanvas-head">
          <div class="offcanvas-title">Menu</div>
          <button id="closeMenuBtn" class="icon-btn" type="button" aria-label="Close menu">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <nav id="mobileNav" class="offcanvas-nav" aria-label="Mobile Navigation"></nav>
      `;
      document.body.appendChild(menu);
    }
  }

  function injectDropdownsIntoDesktopNav() {
    const nav = $("#desktopNav");
    if (!nav) return;

    // Prevent duplicates
    if (nav.querySelector("[data-tsj-dd='1']")) return;

    const ddWrap = document.createElement("div");
    ddWrap.className = "tsj-dd-row";
    ddWrap.setAttribute("data-tsj-dd", "1");

    NAV_GROUPS.forEach((grp) => {
      const box = document.createElement("div");
      box.className = "nav-dd";

      box.innerHTML = `
        <button class="nav-dd-btn" type="button" aria-haspopup="true" aria-expanded="false">
          ${grp.label} <i class="fa-solid fa-chevron-down"></i>
        </button>
        <div class="nav-dd-menu" role="menu"></div>
      `;

      const menu = $(".nav-dd-menu", box);

      grp.items.forEach((it) => {
        const a = document.createElement("a");
        a.className = "nav-dd-item";
        a.setAttribute("role", "menuitem");
        a.href = it.href;
        a.textContent = it.label;
        menu.appendChild(a);
      });

      ddWrap.appendChild(box);
    });

    nav.appendChild(ddWrap);
  }

  function buildMobileNavFromDesktop() {
    const mobileNav = $("#mobileNav");
    if (!mobileNav) return;

    // Always rebuild (so it stays consistent across pages)
    mobileNav.innerHTML = "";

    // Copy existing top-level header links (Home/Results/Search/CSC/Tools/Helpdesk)
    const desktopNav = $("#desktopNav");
    if (desktopNav) {
      const links = $$("a", desktopNav).slice(0, 10);
      links.forEach((a) => {
        const href = a.getAttribute("href");
        const text = a.textContent.trim();
        if (!href || !text) return;
        const item = document.createElement("a");
        item.href = href;
        item.textContent = text;
        mobileNav.appendChild(item);
      });
    }

    NAV_GROUPS.forEach((grp) => {
      const group = document.createElement("div");
      group.className = "offcanvas-group";
      group.innerHTML = `<div class="offcanvas-group-title">${grp.label}</div>`;
      grp.items.forEach((it) => {
        const a = document.createElement("a");
        a.href = it.href;
        a.textContent = it.label;
        group.appendChild(a);
      });
      mobileNav.appendChild(group);
    });
  }

  function initDesktopDropdownBehavior() {
    const dropdowns = $$(".nav-dd");
    if (!dropdowns.length) return;

    const closeAll = () => {
      dropdowns.forEach((dd) => {
        const btn = $(".nav-dd-btn", dd);
        const menu = $(".nav-dd-menu", dd);
        if (!btn || !menu) return;
        btn.setAttribute("aria-expanded", "false");
        menu.classList.remove("open");
      });
    };

    dropdowns.forEach((dd) => {
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if (!btn || !menu) return;

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const isOpen = menu.classList.contains("open");
        closeAll();
        if (!isOpen) {
          menu.classList.add("open");
          btn.setAttribute("aria-expanded", "true");
        }
      });
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".nav-dd")) closeAll();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeAll();
    });

    window.addEventListener("scroll", closeAll, { passive: true });
  }

  // -----------------------
  // OFFCANVAS: fix "stuck" menu
  // -----------------------
  function initOffcanvas() {
    const btn = $("#menuBtn");
    const menu = $("#mobileMenu");
    const overlay = $("#menuOverlay");
    const closeBtn = $("#closeMenuBtn");

    if (!btn || !menu || !overlay || !closeBtn) return;

    const unlockScroll = () => {
      document.body.style.overflow = "";
      document.documentElement.style.overflow = "";
    };

    const close = () => {
      menu.hidden = true;
      overlay.hidden = true;
      overlay.style.pointerEvents = "none";
      btn.setAttribute("aria-expanded", "false");
      unlockScroll();
    };

    const open = () => {
      menu.hidden = false;
      overlay.hidden = false;
      overlay.style.pointerEvents = "auto";
      btn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
      document.documentElement.style.overflow = "hidden";
    };

    // Reset handlers to avoid duplicates
    btn.onclick = open;
    closeBtn.onclick = close;
    overlay.onclick = close;

    menu.addEventListener("click", (e) => {
      const a = e.target.closest("a");
      if (a) close();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 980) close();
    });

    // Safety: if overlay visible but menu hidden -> fix
    setInterval(() => {
      if (menu.hidden && !overlay.hidden) close();
    }, 800);

    window.__TSJ_CLOSE_MENU = close;
  }

  // -----------------------
  // SEARCH: works on pages with search UI present
  // -----------------------
  let SEARCH_INDEX = [];
  let SEARCH_READY = false;

  async function buildSearchIndex() {
    if (SEARCH_READY) return;

    const out = [];

    // dynamic-sections.json (Latest Jobs, Results, etc.)
    try {
      const r = await fetch("dynamic-sections.json", { cache: "no-store" });
      if (r.ok) {
        const d = await r.json();
        (d.sections || []).forEach((sec) => {
          (sec.items || []).forEach((it) => {
            const title = safe(it.name);
            const url = normalizeUrl(it.url || it.link || "");
            if (!title || !url) return;
            out.push({
              title,
              meta: safe(sec.title) || "Updates",
              href: it.external ? url : `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(title)}`,
              external: !!it.external,
            });
          });
        });
      }
    } catch (_) {}

    // jobs.json (categories)
    try {
      const r = await fetch("jobs.json", { cache: "no-store" });
      if (r.ok) {
        const j = await r.json();
        const pool = [...(j.left_jobs || []), ...(j.right_jobs || []), ...(j.top_jobs || [])];
        pool.forEach((it) => {
          if (it && it.title) return;
          const title = safe(it.name);
          const url = normalizeUrl(it.url || it.link || "");
          if (!title || !url) return;
          out.push({
            title,
            meta: "Job Categories",
            href: it.external ? url : `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(title)}`,
            external: !!it.external,
          });
        });
      }
    } catch (_) {}

    // services.json
    try {
      const r = await fetch("services.json", { cache: "no-store" });
      if (r.ok) {
        const s = await r.json();
        const services = Array.isArray(s.services) ? s.services : (Array.isArray(s) ? s : []);
        services.forEach((it) => {
          const title = safe(it.name || it.service);
          const url = normalizeUrl(it.url || it.link || "");
          if (!title || !url) return;
          out.push({ title, meta: "CSC Services", href: url, external: true });
        });
      }
    } catch (_) {}

    // dedupe
    const seen = new Set();
    SEARCH_INDEX = out.filter((x) => {
      const k = (x.title + "|" + x.href).toLowerCase();
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });

    SEARCH_READY = true;
  }

  function initSearch() {
    const input = $("#siteSearchInput");
    const btn = $("#siteSearchBtn");
    const results = $("#searchResults");

    if (!input || !btn || !results) return;

    const escRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

    const run = async () => {
      const q = safe(input.value);
      if (!q) {
        results.classList.remove("open");
        results.innerHTML = "";
        return;
      }

      await buildSearchIndex();

      const ql = q.toLowerCase();
      const matches = SEARCH_INDEX
        .filter((x) => x.title.toLowerCase().includes(ql) || x.meta.toLowerCase().includes(ql))
        .slice(0, 30);

      if (!matches.length) {
        results.classList.add("open");
        results.innerHTML = `
          <div class="result-item">
            <div>
              <div class="result-title">No results found</div>
              <div class="result-meta">Try keywords like SSC, Railway, Police, Admit Card, Result, State name.</div>
            </div>
          </div>
        `;
        return;
      }

      const re = new RegExp(`(${escRe(q)})`, "ig");
      results.classList.add("open");
      results.innerHTML = matches
        .map((m) => {
          const title = safe(m.title).replace(re, "<mark>$1</mark>");
          return `
            <a class="result-item" href="${m.href}" ${m.external ? `target="_blank" rel="noopener"` : ""}>
              <div>
                <div class="result-title">${title}</div>
                <div class="result-meta">${safe(m.meta)}</div>
              </div>
              <div class="result-meta">${m.external ? "↗" : "→"}</div>
            </a>
          `;
        })
        .join("");
    };

    btn.addEventListener("click", run);
    input.addEventListener("input", debounce(run, 140));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") run();
      if (e.key === "Escape") {
        results.classList.remove("open");
        results.innerHTML = "";
        input.blur();
      }
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".search-card")) results.classList.remove("open");
    });
  }

  // -----------------------
  // HOME: render big sections (Latest Jobs etc.) from dynamic-sections.json
  // -----------------------
  function iconForTitle(t) {
    const s = safe(t).toLowerCase();
    if (s.includes("latest job")) return "fa-briefcase";
    if (s.includes("upcoming")) return "fa-clock";
    if (s.includes("admit")) return "fa-id-card";
    if (s.includes("result")) return "fa-square-poll-vertical";
    return "fa-link";
  }
  function colorForTitle(t) {
    const s = safe(t).toLowerCase();
    if (s.includes("latest job")) return "#3b82f6";
    if (s.includes("upcoming")) return "#f59e0b";
    if (s.includes("admit")) return "#10b981";
    if (s.includes("result")) return "#8b5cf6";
    return "#0ea5e9";
  }

  async function renderHomeSections() {
    if (PAGE !== "index.html" && PAGE !== "") return;

    const grid = $("#homeDuoGrid");
    if (!grid) return;

    grid.innerHTML = "";

    let data = null;
    try {
      const r = await fetch("dynamic-sections.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const sections = (data && Array.isArray(data.sections)) ? data.sections : [];
    if (!sections.length) {
      grid.innerHTML = `<div class="seo-block"><strong>No sections found.</strong><p>Check dynamic-sections.json</p></div>`;
      return;
    }

    // pick the 4 key sections if present, otherwise show first 4
    const want = ["Latest Jobs", "Upcoming Jobs", "Admit Cards & Exams Date", "Latest Results"];
    const picked = [];
    want.forEach((name) => {
      const s = sections.find((x) => safe(x.title).toLowerCase() === name.toLowerCase());
      if (s) picked.push(s);
    });
    const finalList = picked.length ? picked : sections.slice(0, 4);

    finalList.forEach((sec) => {
      const title = safe(sec.title);
      const items = Array.isArray(sec.items) ? sec.items : [];

      const card = document.createElement("section");
      card.className = "section-card";

      const col = colorForTitle(title);
      const ic = iconForTitle(title);

      card.innerHTML = `
        <div class="section-head" style="background:${col}">
          <div class="left">
            <i class="fa-solid ${ic}"></i>
            <span>${title}</span>
          </div>
          <a class="view-all" href="search.html" aria-label="View all">View all</a>
        </div>
        <div class="section-body">
          <div class="section-list"></div>
        </div>
      `;

      const list = $(".section-list", card);

      items.slice(0, 12).forEach((it) => {
        const name = safe(it.name);
        const url = normalizeUrl(it.url || it.link || "");
        if (!name || !url) return;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = it.external ? url : `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`;
        if (it.external) {
          a.target = "_blank";
          a.rel = "noopener";
        }
        a.innerHTML = `<div class="t">${name}</div><div class="d">${it.external ? "Open official link" : "Open"}</div>`;
        list.appendChild(a);
      });

      grid.appendChild(card);
    });
  }

  // -----------------------
  // CSC Services page: render services list
  // -----------------------
  async function renderServices() {
    if (PAGE !== "govt-services.html") return;
    const list = $("#servicesList");
    if (!list) return;

    list.innerHTML = "";

    let data = null;
    try {
      const r = await fetch("services.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const services = Array.isArray(data?.services) ? data.services : (Array.isArray(data) ? data : []);
    if (!services.length) {
      list.innerHTML = `<div class="seo-block"><strong>No services found.</strong><p>Check services.json</p></div>`;
      return;
    }

    services.forEach((s) => {
      const name = safe(s.name || s.service);
      const url = normalizeUrl(s.url || s.link || "");
      if (!name || !url) return;

      const a = document.createElement("a");
      a.className = "section-link";
      a.href = url;
      a.target = "_blank";
      a.rel = "noopener";
      a.innerHTML = `<div class="t">${name}</div><div class="d">Open service link</div>`;
      list.appendChild(a);
    });
  }

  // -----------------------
  // SEO content blocks: homepage + page brief
  // -----------------------
  function injectSEOBlocks() {
    const main = $("#main") || $("main");
    if (!main) return;

    if (PAGE === "index.html" || PAGE === "") {
      if ($("#seoHomeBlock")) return;
      const seo = document.createElement("section");
      seo.className = "seo-block";
      seo.id = "seoHomeBlock";
      seo.innerHTML = `
        <h2>Resources to Help Indians Get Government Jobs</h2>
        <p>
          Top Sarkari Jobs helps you find <strong>government job notifications</strong>,
          <strong>online form links</strong>, <strong>admit cards</strong>, and <strong>results</strong>
          from reliable sources. Always verify dates, eligibility, and fees on the official portal.
        </p>

        <div class="seo-grid">
          <div class="seo-card">
            <h3>Why consider a government job?</h3>
            <ul>
              <li>Stable career paths across central and state departments</li>
              <li>Clear eligibility criteria and transparent recruitment schedules</li>
              <li>Opportunities in SSC, Railways, Police, Banking, Defence and more</li>
            </ul>
            <p class="mini-links">
              Explore: <a href="category.html?group=study">Study wise</a> ·
              <a href="category.html?group=popular">Popular categories</a> ·
              <a href="category.html?group=state">State wise</a>
            </p>
          </div>

          <div class="seo-card">
            <h3>How to use this website</h3>
            <ol>
              <li>Open a section like Latest Jobs / Results / Admit Card</li>
              <li>Read the official notice and keep required documents ready</li>
              <li>Re-check the official portal for updates and corrigendum</li>
            </ol>
            <p class="mini-links">
              Quick links: <a href="result.html">Results</a> ·
              <a href="govt-services.html">CSC Services</a> ·
              <a href="search.html">Search</a>
            </p>
          </div>
        </div>
      `;
      main.appendChild(seo);
      return;
    }

    if ($("#pageBriefBlock")) return;

    const map = {
      "result.html": {
        h: "Latest Sarkari Results (Scorecards, Merit Lists, PDFs)",
        p: "Check result links for SSC, Railways, Banking, State boards and more. Always verify roll number and DOB on the official portal.",
      },
      "govt-services.html": {
        h: "CSC Services & Government Schemes",
        p: "Use these service links to access government services. Confirm requirements and any charges on the official portal before submission.",
      },
      "category.html": {
        h: "Browse categories faster",
        p: "Use the category pages to jump to relevant links. Always verify eligibility, last date, and official instructions.",
      },
      "search.html": {
        h: "Search across jobs, results, admit cards and services",
        p: "Type keywords like state name, exam name, board, post, admit card or result to find links quickly.",
      },
      "tools.html": {
        h: "Helpful tools for students and applicants",
        p: "Use tools for PDFs and documents while applying online. Keep files readable and properly sized before uploading.",
      },
    };

    const meta = map[PAGE];
    if (!meta) return;

    const block = document.createElement("section");
    block.className = "seo-block";
    block.id = "pageBriefBlock";
    block.innerHTML = `<h2>${meta.h}</h2><p>${meta.p}</p>`;
    main.appendChild(block);
  }

  // -----------------------
  // Boot
  // -----------------------
  document.addEventListener("DOMContentLoaded", async () => {
    ensureHeaderStructure();
    injectDropdownsIntoDesktopNav();
    initDesktopDropdownBehavior();
    buildMobileNavFromDesktop();
    initOffcanvas();
    initSearch();

    await renderHomeSections();
    await renderServices();

    injectSEOBlocks();
  });
})();
