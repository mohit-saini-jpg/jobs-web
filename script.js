(() => {
  "use strict";

  // ---- Guard (prevents double-init which causes stuck menu) ----
  if (window.__TSJ_BOOTED) return;
  window.__TSJ_BOOTED = true;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const PAGE = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const safe = (v) => (v ?? "").toString().trim();

  const escRE = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  // ---- URL normalization (Fix: CSC links not opening when url missing scheme) ----
  function normalizeUrl(raw) {
    const url = safe(raw);
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    if (url.startsWith("//")) return "https:" + url;
    if (url.startsWith("www.")) return "https://" + url;
    // If it's a relative file path to your own site, keep it as is
    if (url.startsWith("/") || url.endsWith(".html") || url.includes("view.html")) return url;
    // Most external services are missing scheme -> assume https
    return "https://" + url;
  }

  function openInternal(url, name) {
    return `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`;
  }

  // ---- NAV STRUCTURE (rendered on EVERY page) ----
  const NAV = {
    main: [
      { label: "Home", href: "index.html" },
      { label: "Results", href: "result.html" },
      { label: "CSC Services", href: "govt-services.html" },
      { label: "Tools", href: "tools.html" },
      { label: "Helpdesk", href: "helpdesk.html" },
      { label: "Search", href: "search.html" }
    ],
    dropdowns: [
      {
        label: "Jobs",
        items: [
          { label: "Study wise jobs", href: "category.html?group=study" },
          { label: "Popular job categories", href: "category.html?group=popular" },
          { label: "State wise jobs", href: "category.html?group=state" }
        ]
      },
      {
        label: "Admissions",
        items: [
          { label: "Admissions", href: "category.html?group=admissions" },
          { label: "Admit Card / Result / Answer Key / Syllabus", href: "category.html?group=admit-result" }
        ]
      },
      {
        label: "More",
        items: [
          { label: "Latest Khabar", href: "category.html?group=khabar" },
          { label: "Study Material & Top Courses", href: "category.html?group=study-material" }
        ]
      }
    ]
  };

  // ---- Inject HEADER + FOOTER if missing (so dropdown NEVER disappears across pages) ----
  function ensureChrome() {
    // If a page already has .site-header, we’ll ensure required ids exist.
    // If not, we inject a complete header + mobile menu + footer.
    const existingHeader = $(".site-header");

    if (!existingHeader) {
      const header = document.createElement("header");
      header.className = "site-header";
      header.innerHTML = `
        <div class="container header-row">
          <a class="brand" href="index.html" aria-label="Top Sarkari Jobs Home">
            <img src="image.png" alt="Top Sarkari Jobs Logo" class="brand-logo">
            <span class="brand-text">
              <span class="brand-title">Top Sarkari Jobs</span>
              <span class="brand-subtitle">Latest Sarkari Jobs, Results, Admit Cards & Online Forms – 2026</span>
            </span>
          </a>

          <nav class="desktop-nav" id="desktopNav" aria-label="Primary"></nav>

          <div class="header-actions">
            <button id="openSearchBtn" class="icon-btn" type="button" aria-label="Open search">
              <i class="fa-solid fa-magnifying-glass"></i>
            </button>
            <button id="menuBtn" class="icon-btn" type="button" aria-label="Open menu" aria-controls="mobileMenu" aria-expanded="false">
              <i class="fa-solid fa-bars"></i>
            </button>
          </div>
        </div>
      `;
      document.body.prepend(header);
    } else {
      // ensure nav container exists
      if (!$("#desktopNav")) {
        const nav = $(".desktop-nav", existingHeader);
        if (nav) nav.id = "desktopNav";
      }
      // ensure menu button exists for mobile
      if (!$("#menuBtn")) {
        const actions = $(".header-actions", existingHeader) || (() => {
          const a = document.createElement("div");
          a.className = "header-actions";
          $(".header-row", existingHeader)?.appendChild(a);
          return a;
        })();

        actions.innerHTML = `
          <button id="openSearchBtn" class="icon-btn" type="button" aria-label="Open search">
            <i class="fa-solid fa-magnifying-glass"></i>
          </button>
          <button id="menuBtn" class="icon-btn" type="button" aria-label="Open menu" aria-controls="mobileMenu" aria-expanded="false">
            <i class="fa-solid fa-bars"></i>
          </button>
        `;
      }
    }

    // Overlay + Offcanvas always injected (prevents “stuck menu” because markup is consistent)
    if (!$("#menuOverlay")) {
      const overlay = document.createElement("div");
      overlay.id = "menuOverlay";
      overlay.className = "overlay";
      overlay.hidden = true;
      document.body.appendChild(overlay);
    }

    if (!$("#mobileMenu")) {
      const aside = document.createElement("aside");
      aside.id = "mobileMenu";
      aside.className = "offcanvas";
      aside.setAttribute("aria-label", "Mobile menu");
      aside.hidden = true;
      aside.innerHTML = `
        <div class="offcanvas-head">
          <div class="offcanvas-title">Menu</div>
          <button id="closeMenuBtn" class="icon-btn" type="button" aria-label="Close menu">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <nav class="offcanvas-nav" id="mobileNav" aria-label="Mobile primary"></nav>
      `;
      document.body.appendChild(aside);
    }

    if (!$(".site-footer")) {
      const footer = document.createElement("footer");
      footer.className = "site-footer";
      footer.innerHTML = `
        <div class="container footer-row">
          <div>
            <div class="footer-title">Top Sarkari Jobs</div>
            <div class="footer-sub">Government jobs, results, admit cards, services and tools.</div>
            <div class="footer-links">
              <a href="about.html">About</a>
              <a href="contact.html">Contact</a>
              <a href="privacy.html">Privacy</a>
              <a href="terms.html">Terms</a>
            </div>
          </div>
          <div id="footer-social-links" class="footer-social"></div>
        </div>
        <div class="container footer-bottom">© 2025 Top Sarkari Jobs. All rights reserved.</div>
      `;
      document.body.appendChild(footer);
    }
  }

  function buildDesktopNav() {
    const nav = $("#desktopNav");
    if (!nav) return;

    nav.innerHTML = "";

    // main links
    NAV.main.forEach((l) => {
      const a = document.createElement("a");
      a.className = "nav-link";
      a.href = l.href;
      a.textContent = l.label;
      nav.appendChild(a);
    });

    // dropdowns
    NAV.dropdowns.forEach((dd) => {
      const wrap = document.createElement("div");
      wrap.className = "nav-dd";
      wrap.setAttribute("data-dd", "1");

      const btn = document.createElement("button");
      btn.className = "nav-link nav-dd-btn";
      btn.type = "button";
      btn.setAttribute("aria-haspopup", "true");
      btn.setAttribute("aria-expanded", "false");
      btn.innerHTML = `${dd.label} <i class="fa-solid fa-chevron-down"></i>`;

      const menu = document.createElement("div");
      menu.className = "nav-dd-menu";
      menu.setAttribute("role", "menu");

      dd.items.forEach((it) => {
        const a = document.createElement("a");
        a.className = "nav-dd-item";
        a.setAttribute("role", "menuitem");
        a.href = it.href;
        a.textContent = it.label;
        menu.appendChild(a);
      });

      wrap.appendChild(btn);
      wrap.appendChild(menu);
      nav.appendChild(wrap);
    });

    // CTA links injected from header_links.json
    const cta = document.createElement("div");
    cta.id = "header-links";
    cta.className = "header-cta";
    nav.appendChild(cta);
  }

  function buildMobileNav() {
    const nav = $("#mobileNav");
    if (!nav) return;

    nav.innerHTML = "";

    // main links
    NAV.main.forEach((l) => {
      const a = document.createElement("a");
      a.href = l.href;
      a.textContent = l.label;
      nav.appendChild(a);
    });

    // groups
    NAV.dropdowns.forEach((g) => {
      const group = document.createElement("div");
      group.className = "offcanvas-group";
      group.innerHTML = `<div class="offcanvas-group-title">${g.label}</div>`;
      g.items.forEach((it) => {
        const a = document.createElement("a");
        a.href = it.href;
        a.textContent = it.label;
        group.appendChild(a);
      });
      nav.appendChild(group);
    });

    // CTA links injected
    const cta = document.createElement("div");
    cta.id = "header-links-mobile";
    cta.className = "offcanvas-cta";
    nav.appendChild(cta);
  }

  // ---- Load header_links.json for CTA + socials ----
  async function loadHeaderLinks() {
    let data = { header_links: [], social_links: [] };
    try {
      const r = await fetch("header_links.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const links = Array.isArray(data.header_links) ? data.header_links : [];
    const socials = Array.isArray(data.social_links) ? data.social_links : [];

    const desktop = $("#header-links");
    const mobile = $("#header-links-mobile");
    const footerSocial = $("#footer-social-links");

    if (desktop) {
      desktop.innerHTML = "";
      links.forEach((l) => {
        const a = document.createElement("a");
        a.className = "nav-link";
        a.href = normalizeUrl(l.link || l.url || "#");
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = l.name || "Link";
        desktop.appendChild(a);
      });
    }

    if (mobile) {
      mobile.innerHTML = "";
      links.forEach((l) => {
        const a = document.createElement("a");
        a.href = normalizeUrl(l.link || l.url || "#");
        a.target = "_blank";
        a.rel = "noopener";
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

  // ---- Desktop dropdown behavior (close on outside click / escape / scroll) ----
  function initDropdowns() {
    const dds = $$("[data-dd]");
    if (!dds.length) return;

    const closeAll = () => {
      dds.forEach((dd) => {
        const btn = $(".nav-dd-btn", dd);
        const menu = $(".nav-dd-menu", dd);
        if (btn && menu) {
          btn.setAttribute("aria-expanded", "false");
          menu.classList.remove("open");
        }
      });
    };

    dds.forEach((dd) => {
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if (!btn || !menu) return;

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const open = menu.classList.contains("open");
        closeAll();
        if (!open) {
          menu.classList.add("open");
          btn.setAttribute("aria-expanded", "true");
        }
      });
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest("[data-dd]")) closeAll();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeAll();
    });

    window.addEventListener("scroll", closeAll, { passive: true });
  }

  // ---- OFFCANVAS (Fix “stuck menu”) ----
  function initOffcanvas() {
    const btn = $("#menuBtn");
    const closeBtn = $("#closeMenuBtn");
    const menu = $("#mobileMenu");
    const overlay = $("#menuOverlay");

    if (!btn || !closeBtn || !menu || !overlay) return;

    const forceUnlock = () => {
      document.body.style.overflow = "";
      document.documentElement.style.overflow = "";
    };

    const close = () => {
      menu.hidden = true;
      overlay.hidden = true;
      overlay.style.pointerEvents = "none";
      btn.setAttribute("aria-expanded", "false");
      forceUnlock();
    };

    const open = () => {
      menu.hidden = false;
      overlay.hidden = false;
      overlay.style.pointerEvents = "auto";
      btn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
      document.documentElement.style.overflow = "hidden";
    };

    btn.onclick = open;
    closeBtn.onclick = close;
    overlay.onclick = close;

    // close on any link click
    menu.addEventListener("click", (e) => {
      const a = e.target.closest("a");
      if (a) close();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });

    window.addEventListener("beforeunload", close);

    window.addEventListener("resize", () => {
      if (window.innerWidth > 980) close();
    });

    window.__TSJ_CLOSE_MENU = close;

    setInterval(() => {
      const menuOpen = !menu.hidden;
      const overlayOpen = !overlay.hidden;
      if (!menuOpen && overlayOpen) close();
    }, 800);
  }

  // ---- SEARCH (site-wide, fast, uses JSON sources) ----
  let SEARCH_INDEX = [];
  let SEARCH_READY = false;

  async function buildSearchIndex() {
    if (SEARCH_READY) return;

    const out = [];

    // dynamic sections
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
              href: it.external ? url : openInternal(url, title),
              external: !!it.external
            });
          });
        });
      }
    } catch (_) {}

    // jobs.json
    try {
      const r = await fetch("jobs.json", { cache: "no-store" });
      if (r.ok) {
        const j = await r.json();
        const pool = [...(j.top_jobs || []), ...(j.left_jobs || []), ...(j.right_jobs || [])];
        pool.forEach((it) => {
          if (it && it.title) return; // skip headings
          const title = safe(it.name);
          const url = normalizeUrl(it.url || it.link || "");
          if (!title || !url) return;
          out.push({
            title,
            meta: "Jobs / Categories",
            href: it.external ? url : openInternal(url, title),
            external: !!it.external
          });
        });
      }
    } catch (_) {}

    // tools.json
    try {
      const r = await fetch("tools.json", { cache: "no-store" });
      if (r.ok) {
        const t = await r.json();
        ["image", "pdf", "video"].forEach((k) => {
          (t[k] || []).forEach((it) => {
            const title = safe(it.name);
            const url = normalizeUrl(it.url || it.link || "");
            if (!title || !url) return;
            out.push({
              title,
              meta: "Tools",
              href: it.external ? url : openInternal(url, title),
              external: !!it.external
            });
          });
        });
      }
    } catch (_) {}

    // services.json
    try {
      const r = await fetch("services.json", { cache: "no-store" });
      if (r.ok) {
        const s = await r.json();
        const services = (s.services || s || []);
        (services || []).forEach((it) => {
          const title = safe(it.name || it.service);
          const url = normalizeUrl(it.url || it.link || "");
          if (!title || !url) return;
          out.push({
            title,
            meta: "CSC Services",
            href: url,
            external: true
          });
        });
      }
    } catch (_) {}

    const seen = new Set();
    SEARCH_INDEX = out.filter((x) => {
      const key = (x.title + "|" + x.href).toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    SEARCH_READY = true;
  }

  function initSearch() {
    const input = $("#siteSearchInput");
    const btn = $("#siteSearchBtn");
    const results = $("#searchResults");
    const openBtn = $("#openSearchBtn");

    if (!input || !btn || !results) {
      if (openBtn) openBtn.addEventListener("click", () => (location.href = "search.html"));
      return;
    }

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
              <div class="result-meta">Try another keyword (job name, state, exam, board).</div>
            </div>
          </div>
        `;
        return;
      }

      const re = new RegExp(`(${escRE(q)})`, "ig");
      results.classList.add("open");
      results.innerHTML = matches.map((m) => {
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
      }).join("");
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

    if (openBtn) {
      openBtn.addEventListener("click", () => {
        input.scrollIntoView({ behavior: "smooth", block: "center" });
        setTimeout(() => input.focus(), 120);
      });
    }
  }

  function debounce(fn, wait) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), wait);
    };
  }

  // ---- FAQ accordion ----
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

  // =====================================================================
  // ✅ NEW: CONTENT RESTORE (Homepage + Category pages) - NO layout changes
  // =====================================================================

  function iconForTitle(title) {
    const t = safe(title).toLowerCase();
    if (t.includes("latest job")) return "fa-briefcase";
    if (t.includes("upcoming")) return "fa-clock";
    if (t.includes("admit")) return "fa-id-card";
    if (t.includes("result")) return "fa-square-poll-vertical";
    return "fa-link";
  }

  function colorForTitle(title) {
    const t = safe(title).toLowerCase();
    if (t.includes("latest job")) return "#3b82f6";
    if (t.includes("upcoming")) return "#f59e0b";
    if (t.includes("admit")) return "#10b981";
    if (t.includes("result")) return "#8b5cf6";
    return "#0ea5e9";
  }

  // ---- Restore homepage "blue boxes" / top category cards from jobs.json ----
  async function renderHomeCategoryBoxes() {
    if (!(PAGE === "index.html" || PAGE === "")) return;

    // Try common container ids/classes used in your versions
    const mount =
      $("#home-cards") ||
      $("#topLinksGrid") ||
      $("#categoryGrid") ||
      $(".cat-grid");

    if (!mount) return;

    // If already has links, do nothing
    if (mount.querySelector("a")) return;

    let j = null;
    try {
      const r = await fetch("jobs.json", { cache: "no-store" });
      if (r.ok) j = await r.json();
    } catch (_) {}

    if (!j) return;

    const pool = [...(j.top_jobs || []), ...(j.left_jobs || []), ...(j.right_jobs || [])];

    const items = pool
      .filter((it) => it && !it.title)
      .map((it) => {
        const name = safe(it.name);
        const url = normalizeUrl(it.url || it.link || "");
        if (!name || !url) return null;
        return {
          name,
          href: it.external ? url : openInternal(url, name),
          external: !!it.external
        };
      })
      .filter(Boolean)
      .slice(0, 60);

    if (!items.length) return;

    // Do not change structure — just fill using your existing button styles
    mount.innerHTML = items
      .map((x) => {
        const ext = x.external ? ` target="_blank" rel="noopener"` : "";
        // supports both your "home-card" and "job-btn" styling
        const cls = mount.id === "home-cards" ? "home-card" : "job-btn";
        return `<a class="${cls}" href="${x.href}"${ext}>${x.name}</a>`;
      })
      .join("");
  }

  // ---- Restore homepage big sections (Latest Jobs / Upcoming / Admit / Results) from dynamic-sections.json ----
  async function renderHomeBigSections() {
    if (!(PAGE === "index.html" || PAGE === "")) return;

    // Common containers across your builds:
    const mount =
      $("#dynamic-sections") ||
      $("#homeDuoGrid") ||
      $("#sectionsGrid") ||
      $(".duo-grid");

    if (!mount) return;

    // If already has cards, do nothing
    if (mount.querySelector(".section-card")) return;

    let data = null;
    try {
      const r = await fetch("dynamic-sections.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const sections = Array.isArray(data?.sections) ? data.sections : [];
    if (!sections.length) return;

    const want = ["Latest Jobs", "Upcoming Jobs", "Admit Cards & Exams Date", "Latest Results"];
    const picked = [];
    want.forEach((w) => {
      const s = sections.find((x) => safe(x.title).toLowerCase() === w.toLowerCase());
      if (s) picked.push(s);
    });

    const finalList = picked.length ? picked : sections.slice(0, 4);

    mount.innerHTML = "";

    finalList.forEach((sec) => {
      const title = safe(sec.title);
      const items = Array.isArray(sec.items) ? sec.items : [];
      const col = colorForTitle(title);
      const ic = iconForTitle(title);

      const card = document.createElement("section");
      card.className = "section-card";
      card.innerHTML = `
        <div class="section-head" style="background:${col}">
          <div class="left">
            <i class="fa-solid ${ic}"></i>
            <span>${title}</span>
          </div>
        </div>
        <div class="section-body">
          <div class="section-list"></div>
        </div>
      `;

      const list = $(".section-list", card);

      items.slice(0, 25).forEach((it) => {
        const name = safe(it.name);
        const url = normalizeUrl(it.url || it.link || "");
        if (!name || !url) return;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = it.external ? url : openInternal(url, name);
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

  // ---- Restore category.html grid using jobs.json based on ?group= ----
  async function renderCategoryPage() {
    if (PAGE !== "category.html") return;

    const grid =
      $("#categoryGrid") ||
      $("#category-grid") ||
      $(".cat-grid");

    if (!grid) return;

    // If already has links, do nothing
    if (grid.querySelector("a")) return;

    const params = new URLSearchParams(location.search);
    const group = safe(params.get("group") || "study").toLowerCase();

    let j = null;
    try {
      const r = await fetch("jobs.json", { cache: "no-store" });
      if (r.ok) j = await r.json();
    } catch (_) {}

    if (!j) return;

    // Your data is mixed; we keep it simple: show both columns + top
    // (keeps all existing links intact)
    const pool = [...(j.left_jobs || []), ...(j.right_jobs || []), ...(j.top_jobs || [])];

    const items = pool
      .filter((it) => it && !it.title)
      .map((it) => {
        const name = safe(it.name);
        const url = normalizeUrl(it.url || it.link || "");
        if (!name || !url) return null;
        return {
          name,
          href: it.external ? url : openInternal(url, name),
          external: !!it.external
        };
      })
      .filter(Boolean);

    if (!items.length) return;

    // Fill using existing button class
    grid.innerHTML = items
      .slice(0, 120)
      .map((x) => {
        const ext = x.external ? ` target="_blank" rel="noopener"` : "";
        return `<a class="job-btn" href="${x.href}"${ext}>${x.name}</a>`;
      })
      .join("");

    // Optional: if your page has title/desc placeholders, fill them
    const titleEl = $("#category-title");
    const descEl = $("#category-description");
    const titleMap = {
      study: "Study wise jobs",
      popular: "Popular job categories",
      state: "State wise jobs",
      admissions: "Admissions",
      "admit-result": "Admit Card / Result / Answer Key / Syllabus",
      khabar: "Latest Khabar",
      "study-material": "Study Material & Top Courses"
    };
    if (titleEl && titleMap[group]) titleEl.textContent = titleMap[group];
    if (descEl && titleMap[group]) {
      descEl.textContent = "Browse links below. Always verify eligibility and dates on the official portal.";
    }
  }

  // ---- Render CSC services page (Fix links + clickability) ----
  async function renderServicesPage() {
    if (PAGE !== "govt-services.html") return;

    const list = $("#servicesList");
    if (!list) return;

    list.innerHTML = "";

    let data = null;
    try {
      const r = await fetch("services.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const services = (data && (data.services || data)) || [];
    if (!Array.isArray(services) || !services.length) {
      list.innerHTML = `<div class="seo-block"><strong>No services found.</strong><p>Check services.json format.</p></div>`;
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
      a.innerHTML = `
        <div class="t">${name}</div>
        <div class="d">Open service (official / trusted)</div>
      `;
      list.appendChild(a);
    });
  }

  // ---- Render tools page ----
  async function renderToolsPage() {
    if (PAGE !== "tools.html") return;

    const grid = $("#toolsGrid");
    if (!grid) return;

    grid.innerHTML = "";
    grid.classList.add("cat-grid");

    let data = null;
    try {
      const r = await fetch("tools.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const buckets = [
      { key: "image", title: "Image Tools", color: "#0ea5e9" },
      { key: "pdf", title: "PDF Tools", color: "#4f46e5" },
      { key: "video", title: "Video Tools", color: "#db2777" }
    ];

    let any = false;

    buckets.forEach((b) => {
      const items = (data && Array.isArray(data[b.key])) ? data[b.key] : [];
      if (!items.length) return;
      any = true;

      const card = document.createElement("article");
      card.className = "section-card";
      card.innerHTML = `
        <div class="section-head" style="background:${b.color}">
          <div class="left">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
            <span>${b.title}</span>
          </div>
        </div>
        <div class="section-body">
          <div class="section-list"></div>
        </div>
      `;

      const list = $(".section-list", card);

      items.forEach((it) => {
        const name = safe(it.name);
        const url = normalizeUrl(it.url || it.link || "");
        if (!name || !url) return;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = it.external ? url : openInternal(url, name);
        if (it.external) {
          a.target = "_blank";
          a.rel = "noopener";
        }
        a.innerHTML = `<div class="t">${name}</div><div class="d">Open tool</div>`;
        list.appendChild(a);
      });

      grid.appendChild(card);
    });

    if (!any) {
      grid.innerHTML = `<div class="seo-block"><strong>No tools found.</strong><p>Please check tools.json.</p></div>`;
    }
  }

  // ---- SEO content injection (Homepage + page briefs like SarkariResult-style) ----
  function injectSEOContent() {
    if (PAGE === "index.html" || PAGE === "") {
      if (!$("#seoHomeBlock")) {
        const main = $("#main") || $("main") || document.body;
        const block = document.createElement("section");
        block.id = "seoHomeBlock";
        block.className = "seo-block";
        block.innerHTML = `
          <h2>Resources to help you get government jobs</h2>
          <p>
            Looking for the latest <strong>Sarkari Naukri</strong> updates? We organize official links for
            <strong>online forms</strong>, <strong>admit cards</strong>, <strong>results</strong>,
            <strong>answer keys</strong>, and <strong>syllabus</strong> so you can find updates faster.
          </p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Why consider a government job?</h3>
              <ul>
                <li>Stable career paths with transparent recruitment processes</li>
                <li>Opportunities across central + state departments</li>
                <li>Clear eligibility requirements and published timelines</li>
              </ul>
              <p class="mini-links">
                Browse: <a href="category.html?group=study">Study wise</a> ·
                <a href="category.html?group=popular">Popular categories</a> ·
                <a href="category.html?group=state">State wise</a>
              </p>
            </div>
            <div class="seo-card">
              <h3>How to use this website</h3>
              <ol>
                <li>Open a section like Latest Jobs / Results</li>
                <li>Verify eligibility + dates on official portal</li>
                <li>Save the page and re-check for updates</li>
              </ol>
              <p class="mini-links">
                Quick: <a href="result.html">Results</a> ·
                <a href="category.html?group=admit-result">Admit Card / Answer Key</a> ·
                <a href="govt-services.html">CSC Services</a>
              </p>
            </div>
          </div>
        `;
        if (main && main.appendChild) main.appendChild(block);
      }
      return;
    }

    const main = $("#main") || $("main");
    if (!main) return;
    if ($("#pageBriefBlock")) return;

    const titleMap = {
      "result.html": {
        h2: "Latest Results and important updates",
        p: "Check result links, merit lists, score cards and official notices. Always verify your roll number, DOB and board details on the official portal."
      },
      "govt-services.html": {
        h2: "CSC Services and government documents",
        p: "Use these service links to apply for documents and services. Confirm charges, eligibility and requirements on the service portal before submitting."
      },
      "tools.html": {
        h2: "Free tools for students and job seekers",
        p: "Use handy tools for images, PDFs and documents while applying. Keep your files clear, readable and properly sized before uploading to forms."
      },
      "search.html": {
        h2: "Search jobs, results, admit cards and categories",
        p: "Type keywords like board name, state, exam, recruitment or post name to find links faster."
      },
      "helpdesk.html": {
        h2: "Helpdesk & guidance",
        p: "Use helpdesk resources for common form issues, document requirements and where to check official notices."
      },
      "category.html": {
        h2: "Browse categories quickly",
        p: "Use the filter to find a link quickly. Open official portals and confirm last date, eligibility and documents."
      }
    };

    const meta = titleMap[PAGE];
    if (!meta) return;

    const block = document.createElement("section");
    block.id = "pageBriefBlock";
    block.className = "seo-block";
    block.innerHTML = `<h2>${meta.h2}</h2><p>${meta.p}</p>`;
    main.appendChild(block);
  }

  // ---- Boot ----
  document.addEventListener("DOMContentLoaded", async () => {
    ensureChrome();
    buildDesktopNav();
    buildMobileNav();

    await loadHeaderLinks();

    initDropdowns();
    initOffcanvas();
    initSearch();
    initFAQ();

    // ✅ Restore missing content
    await renderHomeCategoryBoxes();
    await renderHomeBigSections();
    await renderCategoryPage();

    injectSEOContent();

    await renderServicesPage();
    await renderToolsPage();
  });

})();
