(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const PAGE = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  const page = PAGE;

  const safe = (v) => (v ?? "").toString().trim();

  const escRE = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  // ---- URL normalization (Fix: CSC links not opening when url missing scheme) ----
  function normalizeUrl(raw) {
    const url = safe(raw);
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    if (url.startsWith("//")) return "https:" + url;
    if (url.startsWith("www.")) return "https://" + url;
    return url;
  }

  // -------------------------
  // Mobile menu (offcanvas)
  // -------------------------
  function initOffcanvas() {
    const menuBtn = $("#menuBtn");
    const mobileMenu = $("#mobileMenu");
    const closeMenuBtn = $("#closeMenuBtn");

    if (!menuBtn || !mobileMenu) return;

    const open = () => {
      mobileMenu.classList.add("open");
      menuBtn.setAttribute("aria-expanded", "true");
      document.body.classList.add("no-scroll");
    };

    const close = () => {
      mobileMenu.classList.remove("open");
      menuBtn.setAttribute("aria-expanded", "false");
      document.body.classList.remove("no-scroll");
    };

    menuBtn.addEventListener("click", () => {
      if (mobileMenu.classList.contains("open")) close();
      else open();
    });

    if (closeMenuBtn) closeMenuBtn.addEventListener("click", close);

    // Click outside
    document.addEventListener("click", (e) => {
      if (!mobileMenu.classList.contains("open")) return;
      const isInside = mobileMenu.contains(e.target) || menuBtn.contains(e.target);
      if (!isInside) close();
    });

    // ESC closes
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });
  }

  // -------------------------
  // Desktop dropdowns (hover-safe)
  // -------------------------
  function initDropdowns() {
    const dropdowns = $$("[data-dd]");
    if (!dropdowns.length) return;

    dropdowns.forEach((dd) => {
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if (!btn || !menu) return;

      let closeTimer = null;

      const open = () => {
        clearTimeout(closeTimer);
        dd.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
      };

      const close = () => {
        dd.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
      };

      // Hover with small delay (prevents disappearing when moving to items)
      dd.addEventListener("mouseenter", open);
      dd.addEventListener("mouseleave", () => {
        clearTimeout(closeTimer);
        closeTimer = setTimeout(close, 160);
      });

      // Click toggle for accessibility
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        if (dd.classList.contains("open")) close();
        else open();
      });

      // Click outside closes
      document.addEventListener("click", (e) => {
        if (!dd.classList.contains("open")) return;
        const inside = dd.contains(e.target);
        if (!inside) close();
      });

      // Keyboard close
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") close();
      });
    });
  }

  // -------------------------
  // FAQ accordion
  // -------------------------
  function initFAQ() {
    const buttons = $$(".faq-q");
    if (!buttons.length) return;

    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const expanded = btn.getAttribute("aria-expanded") === "true";
        buttons.forEach((b) => {
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

  // -------------------------
  // View helper
  // -------------------------
  function openInternal(url, name) {
    return `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`;
  }

  // -------------------------
  // Category page (category.html?group=...)
  // -------------------------
  function getCategoryGroups() {
    // Safe defaults: always-working links (Google search via view.html).
    // If you later want specific URLs, just replace the `url` values here.
    return {
      "study": {
        title: "Study wise jobs",
        desc: "Browse jobs by education level and qualification.",
        items: [
          { name: "8th Pass Jobs", url: "https://www.google.com/search?q=8th+pass+sarkari+jobs" },
          { name: "10th Pass Jobs", url: "https://www.google.com/search?q=10th+pass+sarkari+jobs" },
          { name: "12th Pass Jobs", url: "https://www.google.com/search?q=12th+pass+sarkari+jobs" },
          { name: "ITI Jobs", url: "https://www.google.com/search?q=ITI+sarkari+jobs" },
          { name: "Diploma Jobs", url: "https://www.google.com/search?q=diploma+sarkari+jobs" },
          { name: "Graduate Jobs", url: "https://www.google.com/search?q=graduate+sarkari+jobs" },
          { name: "Post Graduate Jobs", url: "https://www.google.com/search?q=post+graduate+sarkari+jobs" }
        ]
      },
      "popular": {
        title: "Popular job categories",
        desc: "Popular government job categories people search for the most.",
        items: [
          { name: "SSC Jobs", url: "https://www.google.com/search?q=SSC+jobs+online+form" },
          { name: "Railway Jobs", url: "https://www.google.com/search?q=railway+recruitment+jobs" },
          { name: "Bank Jobs", url: "https://www.google.com/search?q=bank+recruitment+jobs" },
          { name: "Police Jobs", url: "https://www.google.com/search?q=police+recruitment+jobs" },
          { name: "Teaching Jobs", url: "https://www.google.com/search?q=teaching+government+jobs" },
          { name: "Defence Jobs", url: "https://www.google.com/search?q=defence+recruitment+jobs" },
          { name: "UPSC Jobs", url: "https://www.google.com/search?q=UPSC+recruitment+jobs" },
          { name: "State PSC Jobs", url: "https://www.google.com/search?q=state+PSC+recruitment+jobs" }
        ]
      },
      "state": {
        title: "State wise jobs",
        desc: "State specific government job updates and recruitments.",
        items: [
          { name: "UP Jobs", url: "https://www.google.com/search?q=UP+government+jobs" },
          { name: "Bihar Jobs", url: "https://www.google.com/search?q=Bihar+government+jobs" },
          { name: "MP Jobs", url: "https://www.google.com/search?q=Madhya+Pradesh+government+jobs" },
          { name: "Rajasthan Jobs", url: "https://www.google.com/search?q=Rajasthan+government+jobs" },
          { name: "Delhi Jobs", url: "https://www.google.com/search?q=Delhi+government+jobs" },
          { name: "Maharashtra Jobs", url: "https://www.google.com/search?q=Maharashtra+government+jobs" },
          { name: "Gujarat Jobs", url: "https://www.google.com/search?q=Gujarat+government+jobs" },
          { name: "Punjab Jobs", url: "https://www.google.com/search?q=Punjab+government+jobs" }
        ]
      },
      "admissions": {
        title: "Admissions",
        desc: "Admission forms, notices and important education updates.",
        items: [
          { name: "Latest Admissions", url: "https://www.google.com/search?q=latest+admission+forms+india" },
          { name: "Entrance Exams", url: "https://www.google.com/search?q=upcoming+entrance+exams+india" },
          { name: "Scholarships", url: "https://www.google.com/search?q=scholarships+india+apply+online" },
          { name: "University Admissions", url: "https://www.google.com/search?q=university+admission+forms+india" }
        ]
      },
      "admit-result": {
        title: "Admit Card / Result / Answer Key / Syllabus",
        desc: "Quick links to admit cards, results, answer keys and syllabus.",
        items: [
          { name: "Admit Card", url: "https://www.google.com/search?q=admit+card+download" },
          { name: "Result", url: "https://www.google.com/search?q=latest+result+government+exam" },
          { name: "Answer Key", url: "https://www.google.com/search?q=answer+key+government+exam" },
          { name: "Syllabus", url: "https://www.google.com/search?q=syllabus+government+exam+pdf" }
        ]
      },
      "khabar": {
        title: "Latest Khabar",
        desc: "Latest updates and important news related to jobs and exams.",
        items: [
          { name: "Latest Sarkari Updates", url: "https://www.google.com/search?q=latest+sarkari+job+news" },
          { name: "Exam Calendar Updates", url: "https://www.google.com/search?q=exam+calendar+government+jobs" },
          { name: "Important Notices", url: "https://www.google.com/search?q=important+notice+recruitment" }
        ]
      },
      "study-material": {
        title: "Study Material & Top Courses",
        desc: "Study material, practice sets and learning resources.",
        items: [
          { name: "Free Mock Tests", url: "https://www.google.com/search?q=free+mock+tests+ssc+railway" },
          { name: "Previous Year Papers", url: "https://www.google.com/search?q=previous+year+papers+ssc+railway+pdf" },
          { name: "Top Online Courses", url: "https://www.google.com/search?q=best+online+courses+for+government+exams" }
        ]
      }
    };
  }

  function initCategoryPage() {
    const grid = $("#categoryGrid");
    const titleEl = $("#categoryTitle");
    const descEl = $("#categoryDesc");
    const crumbEl = $("#crumbText");
    const filterInput = $("#categoryFilter");
    const clearBtn = $("#clearCategoryFilter");
    const emptyEl = $("#categoryEmpty");

    if (!grid || !titleEl || !descEl || !crumbEl) return;

    const params = new URLSearchParams(location.search);
    const group = safe(params.get("group")) || "study";

    const groups = getCategoryGroups();
    const cfg = groups[group] || groups["study"];

    titleEl.textContent = cfg.title || "Category";
    crumbEl.textContent = cfg.title || "Category";
    descEl.textContent = cfg.desc || "";

    const allItems = Array.isArray(cfg.items) ? cfg.items.slice() : [];

    const render = () => {
      const q = safe(filterInput ? filterInput.value : "").toLowerCase();
      const filtered = !q ? allItems : allItems.filter(it => safe(it.name).toLowerCase().includes(q));

      grid.innerHTML = "";
      (filtered || []).forEach(it => {
        const name = safe(it.name);
        const url = safe(it.url);
        if (!name || !url) return;

        const a = document.createElement("a");
        a.className = "section-link"; // reuse existing styling
        a.href = openInternal(url, name);
        a.innerHTML = `<div class="t">${name}</div><div class="d">Open</div>`;
        grid.appendChild(a);
      });

      const has = (filtered || []).length > 0;
      if (emptyEl) emptyEl.style.display = has ? "none" : "block";
    };

    if (filterInput) filterInput.addEventListener("input", render);
    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        if (filterInput) filterInput.value = "";
        render();
      });
    }

    render();
  }

  // -------------------------
  // Homepage big sections (dynamic-sections.json)
  // -------------------------
  async function renderHomepageSections() {
    const wrap = $("#dynamic-sections");
    if (!wrap) return;

    let data = { sections: [] };
    try {
      const r = await fetch("dynamic-sections.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    wrap.innerHTML = "";

    const isHomePageCta = (name, url) => {
      const n = safe(name).toLowerCase();
      const u = safe(url).toLowerCase();

      return (
        n.includes("ai helpdesk") ||
        n.includes("resume") ||
        n.includes("whatsapp") ||
        n.includes("join") ||
        n.includes("contact") ||
        n.includes("about") ||
        n.includes("privacy") ||
        n.includes("terms") ||
        n.includes("helpdesk") ||
        n.includes("tools") ||
        n.includes("csc") ||
        n.includes("services") ||
        n.includes("╰┈➤") ||
        (u.includes("topsarkarijobs.com") && (n.includes("home page") || n.includes("main home")))
      );
    };

    (data.sections || []).forEach((sec) => {
      const title = safe(sec.title) || "Updates";
      const color = safe(sec.color) || "#0284c7";
      const icon = safe(sec.icon) || "fa-solid fa-briefcase";

      const card = document.createElement("article");
      card.className = "section-card";
      card.innerHTML = `
        <div class="section-head" style="background:${color}">
          <div class="left">
            <i class="${icon}"></i>
            <span>${title}</span>
          </div>
        </div>
        <div class="section-body">
          <div class="section-list"></div>
          ${sec.viewMoreUrl ? `<a class="view-all" href="${openInternal(sec.viewMoreUrl, title)}">View All <i class="fa-solid fa-arrow-right"></i></a>` : ""}
        </div>
      `;

      const list = $(".section-list", card);
      const items = Array.isArray(sec.items) ? sec.items.slice(0, 8) : [];
      items.forEach((it) => {
        const name = safe(it.name) || "Open";
        const url = it.url || it.link || "";
        if (!url) return;

        if (isHomePageCta(name, url)) return;

        const external = !!it.external;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = external ? normalizeUrl(url) : openInternal(url, name);
        if (external) {
          a.target = "_blank";
          a.rel = "noopener";
        }

        a.innerHTML = `
          <div class="t">${name}</div>
          ${it.date ? `<div class="d">${safe(it.date)}</div>` : `<div class="d">Open official link</div>`}
        `;
        list.appendChild(a);
      });

      wrap.appendChild(card);
    });
  }

  // -------------------------
  // Header/footer links (from header_links.json)
  // -------------------------
  async function loadHeaderLinks() {
    let data = { header_links: [], social_links: [] };
    try {
      const r = await fetch("header_links.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const desktop = $("#header-links");
    const mobile = $("#header-links-mobile");
    if (!desktop && !mobile) return;

    const links = Array.isArray(data.header_links) ? data.header_links : [];

    const renderLinks = (root) => {
      if (!root) return;
      root.innerHTML = "";
      links.forEach((l) => {
        const name = safe(l.name);
        const href = safe(l.href);
        if (!name || !href) return;

        const a = document.createElement("a");
        a.className = "cta-link";
        a.href = href;
        if (href.startsWith("http")) {
          a.target = "_blank";
          a.rel = "noopener";
        }
        a.textContent = name;
        root.appendChild(a);
      });
    };

    renderLinks(desktop);
    renderLinks(mobile);
  }

  // -------------------------
  // Search overlay (global)
  // -------------------------
  function initSearch() {
    const openBtn = $("#openSearchBtn");
    const overlay = $("#searchOverlay");
    const closeBtn = $("#closeSearchBtn");
    const input = $("#globalSearchInput");
    const results = $("#globalSearchResults");

    if (!openBtn || !overlay || !closeBtn || !input || !results) return;

    const open = () => {
      overlay.classList.add("open");
      document.body.classList.add("no-scroll");
      input.focus();
    };
    const close = () => {
      overlay.classList.remove("open");
      document.body.classList.remove("no-scroll");
      input.value = "";
      results.innerHTML = "";
      results.classList.remove("open");
    };

    openBtn.addEventListener("click", open);
    closeBtn.addEventListener("click", close);

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });

    const index = [
      { title: "Home", href: "index.html", meta: "Top Sarkari Jobs home" },
      { title: "Results", href: "result.html", meta: "Latest results" },
      { title: "CSC Services", href: "govt-services.html", meta: "Common Service Center services" },
      { title: "Tools", href: "tools.html", meta: "Useful tools" },
      { title: "Helpdesk", href: "helpdesk.html", meta: "Support and guides" },
      { title: "Study wise jobs", href: "category.html?group=study", meta: "Jobs by education level" },
      { title: "Popular job categories", href: "category.html?group=popular", meta: "Top categories" },
      { title: "State wise jobs", href: "category.html?group=state", meta: "Jobs by state" },
      { title: "Admissions", href: "category.html?group=admissions", meta: "Admissions and forms" },
      { title: "Admit Card / Result / Answer Key / Syllabus", href: "category.html?group=admit-result", meta: "Admit/result/syllabus" },
      { title: "Latest Khabar", href: "category.html?group=khabar", meta: "News & updates" },
      { title: "Study Material & Top Courses", href: "category.html?group=study-material", meta: "Courses & material" }
    ];

    const run = () => {
      const q = safe(input.value).toLowerCase();
      if (!q) {
        results.classList.remove("open");
        results.innerHTML = "";
        return;
      }

      const matches = index
        .filter(
          (x) =>
            safe(x.title).toLowerCase().includes(q) ||
            safe(x.meta).toLowerCase().includes(q)
        )
        .slice(0, 12);

      if (!matches.length) {
        results.classList.add("open");
        results.innerHTML = `
          <div class="result-item">
            <div>
              <div class="t">No results</div>
              <div class="d">Try different keywords</div>
            </div>
          </div>`;
        return;
      }

      results.classList.add("open");
      results.innerHTML = "";
      matches.forEach((m) => {
        const a = document.createElement("a");
        a.className = "result-item";
        a.href = m.href;
        a.innerHTML = `
          <div>
            <div class="t">${safe(m.title)}</div>
            <div class="d">${safe(m.meta)}</div>
          </div>
          <i class="fa-solid fa-arrow-right"></i>
        `;
        results.appendChild(a);
      });
    };

    input.addEventListener("input", run);
  }

  // -------------------------
  // Page routers
  // -------------------------
  async function renderCategoryPage() {
    if (page !== "category.html") return;
    initCategoryPage();
  }

  async function renderServicesPage() {
    if (page !== "govt-services.html") return;
    // keep your existing services renderer if you have one in other versions
  }

  async function renderToolsPage() {
    if (page !== "tools.html") return;
    // keep your existing tools renderer if you have one in other versions
  }

  document.addEventListener("DOMContentLoaded", async () => {
    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    initFAQ();
    initSearch();

    if (page === "index.html" || page === "") {
      await renderHomepageSections();
    }

    await renderCategoryPage();
    await renderServicesPage();
    await renderToolsPage();
  });
})();
