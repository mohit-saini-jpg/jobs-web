(() => {
  "use strict";

  // Prevent double-init
  if (window.__TSJ_BOOTED) return;
  window.__TSJ_BOOTED = true;

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const safe = (v) => (v ?? "").toString().trim();
  const escRE = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  // -------- URL normalization (fix missing scheme) --------
  function normalizeUrl(raw) {
    const url = safe(raw);
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    if (url.startsWith("//")) return "https:" + url;
    if (url.startsWith("www.")) return "https://" + url;
    if (url.startsWith("/") || url.endsWith(".html") || url.includes("view.html")) return url;
    return "https://" + url;
  }

  function openInternal(url, name) {
    return `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`;
  }

  // Remove repeated "Main Home Page" CTA-ish links that clutter sections
  const isHomePageCta = (name, url) => {
    const n = safe(name).toLowerCase();
    const u = safe(url).toLowerCase();
    return (
      n.includes("website का main home page") ||
      n.includes("main home page") ||
      (n.includes("🏠") && n.includes("home page")) ||
      n.includes("╰┈➤") ||
      (u.includes("topsarkarijobs.com") && (n.includes("home page") || n.includes("main home")))
    );
  };

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
    const footerSocial = $("#footer-social-links");

    const links = Array.isArray(data.header_links) ? data.header_links : [];
    const socials = Array.isArray(data.social_links) ? data.social_links : [];

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

  // -------------------------
  // Offcanvas (mobile menu)
  // -------------------------
  function initOffcanvas() {
    const overlay = $("#menuOverlay");
    const menu = $("#mobileMenu");
    const openBtn = $("#menuBtn");
    const closeBtn = $("#closeMenuBtn");

    if (!overlay || !menu || !openBtn || !closeBtn) return;

    const open = () => {
      overlay.hidden = false;
      menu.hidden = false;
      overlay.style.pointerEvents = "auto";
      openBtn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
      document.documentElement.style.overflow = "hidden";
    };

    const close = () => {
      overlay.hidden = true;
      menu.hidden = true;
      overlay.style.pointerEvents = "none";
      openBtn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
      document.documentElement.style.overflow = "";
    };

    // Prevent double binding (in case)
    openBtn.onclick = open;
    closeBtn.onclick = close;
    overlay.onclick = close;

    // close on any menu link click
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

    window.__closeMenu = close;
  }

  // -------------------------
  // Desktop dropdowns (hover-friendly + click toggle)
  // -------------------------
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
        if (dd.__ddCloseTimer) {
          clearTimeout(dd.__ddCloseTimer);
          dd.__ddCloseTimer = null;
        }
      });
    };

    const scheduleClose = (dd, delay = 160) => {
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if (!btn || !menu) return;

      if (dd.__ddCloseTimer) clearTimeout(dd.__ddCloseTimer);
      dd.__ddCloseTimer = setTimeout(() => {
        menu.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
        dd.__ddCloseTimer = null;
      }, delay);
    };

    dds.forEach((dd) => {
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if (!btn || !menu) return;

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const isOpen = menu.classList.contains("open");
        if (dd.__ddCloseTimer) {
          clearTimeout(dd.__ddCloseTimer);
          dd.__ddCloseTimer = null;
        }
        closeAll();
        if (!isOpen) {
          menu.classList.add("open");
          btn.setAttribute("aria-expanded", "true");
        }
      });

      dd.addEventListener("mouseenter", () => {
        if (window.matchMedia("(hover:hover)").matches) {
          closeAll();
          menu.classList.add("open");
          btn.setAttribute("aria-expanded", "true");
        }
      });

      dd.addEventListener("mouseleave", () => {
        if (window.matchMedia("(hover:hover)").matches) {
          scheduleClose(dd, 160);
        }
      });

      menu.addEventListener("mouseenter", () => {
        if (dd.__ddCloseTimer) {
          clearTimeout(dd.__ddCloseTimer);
          dd.__ddCloseTimer = null;
        }
      });

      menu.addEventListener("mouseleave", () => {
        if (window.matchMedia("(hover:hover)").matches) {
          scheduleClose(dd, 160);
        }
      });
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest("[data-dd]")) closeAll();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeAll();
    });
  }

  // -------------------------
  // FAQ accordion
  // -------------------------
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
        const raw = it.url || it.link || "";
        if (!raw) return;
        if (isHomePageCta(name, raw)) return;

        const external = !!it.external;
        const url = normalizeUrl(raw);

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = external ? url : openInternal(url, name);
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
  // Category pages ✅ FIXED (Study/Popular/State + Admissions/More pages)
  // Reads:
  // - jobs.json for study/popular/state (buttons)
  // - dynamic-sections.json for admissions/admit-result/khabar/study-material (link list)
  // -------------------------
  async function renderCategoryPage() {
    if (page !== "category.html") return;

    const params = new URLSearchParams(location.search);
    const group = safe(params.get("group") || "study").toLowerCase();

    // Prefer these container IDs; supports multiple category.html versions
    const grid =
      $("#category-grid") ||
      $("#categoryGrid") ||
      $("#category-grid-links") ||
      $("#categoryLinks") ||
      $(".cat-grid") ||
      $(".section-list");

    if (!grid) return;

    // Do not wipe if already has links (helps if you manually added content)
    if (grid.querySelector("a")) return;

    const titleEl = $("#category-title") || $("h1");
    const descEl = $("#category-description");

    const meta = {
      study: { t: "Study wise jobs", d: "Browse government jobs by education level and eligibility." },
      popular: { t: "Popular job categories", d: "Explore popular government job categories and departments." },
      state: { t: "State wise jobs", d: "Find government jobs by Indian states and region-wise recruitment." },
      admissions: { t: "Admissions", d: "Admissions, applications, counseling and important academic forms." },
      "admit-result": { t: "Admit Card / Result / Answer Key / Syllabus", d: "Quick links for admit cards, results, answer keys and syllabus updates." },
      khabar: { t: "Latest Khabar", d: "Important updates, notices and recruitment news." },
      "study-material": { t: "Study Material & Top Courses", d: "Useful study resources and preparation materials." }
    };

    if (titleEl && meta[group]) titleEl.textContent = meta[group].t;
    if (descEl && meta[group]) descEl.textContent = meta[group].d;

    // Helper renderers
    const renderButtons = (items) => {
      grid.classList.add("cat-grid");
      grid.innerHTML = items
        .map((x) => {
          const ext = x.external ? ` target="_blank" rel="noopener"` : "";
          return `<a class="job-btn" href="${x.href}"${ext}>${x.name}</a>`;
        })
        .join("");
    };

    const renderListCards = (items) => {
      // If page uses a section-list style, keep it (don’t force grid)
      grid.innerHTML = items
        .map((x) => {
          const ext = x.external ? ` target="_blank" rel="noopener"` : "";
          return `
            <a class="section-link" href="${x.href}"${ext}>
              <div class="t">${x.name}</div>
              <div class="d">${x.meta || "Open official link"}</div>
            </a>
          `;
        })
        .join("");
    };

    // 1) Study/Popular/State → use jobs.json
    if (group === "study" || group === "popular" || group === "state") {
      let j = null;
      try {
        const r = await fetch("jobs.json", { cache: "no-store" });
        if (r.ok) j = await r.json();
      } catch (_) {}

      const pool = [
        ...(j?.left_jobs || []),
        ...(j?.right_jobs || []),
        ...(j?.top_jobs || [])
      ];

      const items = pool
        .filter((it) => it && !it.title)
        .map((it) => {
          const name = safe(it.name);
          const raw = it.url || it.link || "";
          if (!name || !raw) return null;
          const url = normalizeUrl(raw);
          const external = !!it.external;
          return {
            name,
            href: external ? url : openInternal(url, name),
            external
          };
        })
        .filter(Boolean)
        .slice(0, 180);

      if (items.length) {
        renderButtons(items);
        return;
      }
      // If jobs.json fails, fallthrough to dynamic-sections fallback below
    }

    // 2) Admissions / Admit-Result / Khabar / Study Material → use dynamic-sections.json
    let d = null;
    try {
      const r = await fetch("dynamic-sections.json", { cache: "no-store" });
      if (r.ok) d = await r.json();
    } catch (_) {}

    const sectionTitleByGroup = {
      admissions: ["admission", "counseling", "application"],
      "admit-result": ["admit", "result", "answer key", "syllabus"],
      khabar: ["khabar", "news", "update"],
      "study-material": ["study material", "course", "mock", "books", "notes"]
    };

    const needles = sectionTitleByGroup[group] || [];
    const sections = Array.isArray(d?.sections) ? d.sections : [];

    // Choose sections that match keywords in title
    const matched = sections.filter((s) => {
      const t = safe(s.title).toLowerCase();
      return needles.some((n) => t.includes(n));
    });

    // Combine all items from matched sections; if none matched, use all sections (safe fallback)
    const useSections = matched.length ? matched : sections;

    const items = [];
    useSections.forEach((sec) => {
      const secTitle = safe(sec.title) || "Updates";
      (sec.items || []).forEach((it) => {
        const name = safe(it.name);
        const raw = it.url || it.link || "";
        if (!name || !raw) return;
        if (isHomePageCta(name, raw)) return;

        const url = normalizeUrl(raw);
        const external = !!it.external;

        items.push({
          name,
          href: external ? url : openInternal(url, name),
          external,
          meta: secTitle
        });
      });
    });

    // Final fallback: if still nothing, show a helpful message
    if (!items.length) {
      grid.innerHTML = `
        <div class="seo-block">
          <strong>Links not found for this category.</strong>
          <p>Please confirm <code>jobs.json</code> and <code>dynamic-sections.json</code> are present in the same folder as category.html.</p>
        </div>
      `;
      return;
    }

    // For these pages, list cards look better than endless buttons
    renderListCards(items.slice(0, 200));
  }

  // -------------------------
  // CSC Services page renderer ✅ FIXED (normalizeUrl so links open)
  // -------------------------
  async function renderServicesPage() {
    if (page !== "govt-services.html") return;

    const list = $("#servicesList");
    if (!list) return;

    let data = null;
    try {
      const r = await fetch("services.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const services = (data && (data.services || data)) || [];
    list.innerHTML = "";

    if (!Array.isArray(services) || !services.length) {
      list.innerHTML = `<div class="seo-block"><strong>No services found.</strong><p>Please check services.json.</p></div>`;
      return;
    }

    services.forEach((s) => {
      const name = safe(s.name || s.service);
      const raw = s.url || s.link || "";
      const url = normalizeUrl(raw);
      if (!name || !url) return;

      const a = document.createElement("a");
      a.className = "section-link";
      a.href = url;
      a.target = "_blank";
      a.rel = "noopener";
      a.innerHTML = `
        <div class="t">${name}</div>
        <div class="d">Open service</div>
      `;
      list.appendChild(a);
    });
  }

  // -------------------------
  // Tools page renderer ✅ (if tools.html has #toolsGrid)
  // -------------------------
  async function renderToolsPage() {
    if (page !== "tools.html") return;

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
      { key: "image", title: "Image Tools" },
      { key: "pdf", title: "PDF Tools" },
      { key: "video", title: "Video Tools" }
    ];

    let any = false;

    buckets.forEach((b) => {
      const items = Array.isArray(data?.[b.key]) ? data[b.key] : [];
      if (!items.length) return;
      any = true;

      const card = document.createElement("article");
      card.className = "section-card";
      card.innerHTML = `
        <div class="section-head">
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
        const raw = it.url || it.link || "";
        if (!name || !raw) return;

        const url = normalizeUrl(raw);
        const external = !!it.external;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = external ? url : openInternal(url, name);
        if (external) {
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

  // -------------------------
  // Search (light index; your big search can be expanded later)
  // -------------------------
  function initSearch() {
    const input = $("#siteSearchInput");
    const btn = $("#siteSearchBtn");
    const results = $("#searchResults");
    const openBtn = $("#openSearchBtn");

    if (!input || !btn || !results) return;

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
        .filter((x) => safe(x.title).toLowerCase().includes(q) || safe(x.meta).toLowerCase().includes(q))
        .slice(0, 12);

      if (!matches.length) {
        results.classList.add("open");
        results.innerHTML = `
          <div class="result-item">
            <div>
              <div class="result-title">No results found</div>
              <div class="result-meta">Try a different keyword.</div>
            </div>
          </div>
        `;
        return;
      }

      const re = new RegExp(`(${escRE(q)})`, "ig");
      results.classList.add("open");
      results.innerHTML = matches
        .map((m) => {
          const title = safe(m.title).replace(re, "<mark>$1</mark>");
          return `
            <a class="result-item" href="${m.href}">
              <div>
                <div class="result-title">${title}</div>
                <div class="result-meta">${safe(m.meta)}</div>
              </div>
              <div class="result-meta">→</div>
            </a>
          `;
        })
        .join("");
    };

    btn.addEventListener("click", run);
    input.addEventListener("input", debounce(run, 150));
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
        setTimeout(() => input.focus(), 150);
      });
    }
  }

  function debounce(fn, wait) {
    let t = null;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), wait);
    };
  }

  // -------------------------
  // Boot
  // -------------------------
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
