(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const safe = (v) => (v ?? "").toString().trim();
  const escRE = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  function normalizeUrl(raw) {
    const s = safe(raw);
    if (!s) return "";
    if (/^(https?:)?\/\//i.test(s) || /^(mailto:|tel:)/i.test(s)) return s;
    if (s.startsWith("#") || s.startsWith("?")) return s;
    if (s.startsWith("/") || s.endsWith(".html") || s.startsWith("./") || s.startsWith("../")) return s;
    return "https://" + s.replace(/^\/+/, "");
  }

  // External URL wrapper (used on homepage dynamic sections + tools)
  function openInternal(url, name) {
    const u = normalizeUrl(url);
    return `view.html?url=${encodeURIComponent(u)}&name=${encodeURIComponent(name)}`;
  }

  // Used by tools.html header back button
  window.goBack = () => {
    if (window.history.length > 1) window.history.back();
    else window.location.href = "index.html";
  };

  // ✅ NEW: Inject same homepage header/footer everywhere (Results now, other pages later)
  async function injectHeaderFooter() {
    const headerHost = document.getElementById("site-header");
    const footerHost = document.getElementById("site-footer");
    if (!headerHost && !footerHost) return;

    async function loadFirstWorking(paths) {
      for (const p of paths) {
        try {
          const r = await fetch(p, { cache: "no-store" });
          if (r.ok) return await r.text();
        } catch (_) {}
      }
      return "";
    }

    if (headerHost) {
      const headerHtml = await loadFirstWorking(["header.html", "./header.html", "/header.html"]);
      if (headerHtml) headerHost.innerHTML = headerHtml;
    }

    if (footerHost) {
      const footerHtml = await loadFirstWorking(["footer.html", "./footer.html", "/footer.html"]);
      if (footerHtml) footerHost.innerHTML = footerHtml;
    }
  }

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

  // ---------------------------
  // Mobile menu (fixed)
  // ---------------------------
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

  // ---------------------------
  // Desktop dropdowns (fixed hover gap)
  // ---------------------------
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
      dds.forEach((dd) => {
        clearTimer(dd);
        setOpen(dd, false);
      });
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

      dd.addEventListener("focusin", () => {
        if (!canHover()) return;
        clearTimer(dd);
        closeAll();
        setOpen(dd, true);
      });
      dd.addEventListener("focusout", (e) => {
        if (!dd.contains(e.relatedTarget)) scheduleClose(dd);
      });
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest("[data-dd]")) closeAll();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeAll();
    });
  }

  // ---------------------------
  // FAQ accordion
  // ---------------------------
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

  // ---------------------------
  // Homepage dynamic sections (dynamic-sections.json)
  // ---------------------------
  async function renderHomepageSections() {
    if (!(page === "index.html" || page === "")) return;

    const host = document.getElementById("dynamic-sections");
    if (!host) return;

    let data = null;
    try {
      const r = await fetch("dynamic-sections.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    if (!data || !Array.isArray(data.sections)) return;

    host.innerHTML = "";

    data.sections.forEach((section) => {
      const title = safe(section.title);
      const items = Array.isArray(section.items) ? section.items.slice(0, 8) : [];

      const wrap = document.createElement("section");
      wrap.className = "dynamic-section";

      const header = document.createElement("div");
      header.className = "dynamic-section-header";

      const h3 = document.createElement("h3");
      h3.textContent = title || "Section";

      const more = document.createElement("a");
      more.className = "more-link";
      more.href = `view.html?section=${encodeURIComponent(title)}`;
      more.textContent = "More";

      header.appendChild(h3);
      header.appendChild(more);

      const list = document.createElement("div");
      list.className = "dynamic-list";

      items.forEach((it) => {
        const name = safe(it.name);
        const url = safe(it.url);

        const a = document.createElement("a");
        a.className = "dynamic-item";
        a.href = openInternal(url, name);
        a.innerHTML = `
          <div class="dynamic-item-title">${name || "Open"}</div>
          <div class="dynamic-item-sub">Open official link</div>
        `;
        list.appendChild(a);
      });

      wrap.appendChild(header);
      wrap.appendChild(list);
      host.appendChild(wrap);
    });
  }

  // ---------------------------
  // Homepage colorful headline buttons (from header_links.json -> home_links)
  // ---------------------------
  async function renderHomeQuickLinks() {
    if (!(page === "index.html" || page === "")) return;

    // Find where to insert: right above the homepage search bar/section
    const searchInput =
      document.getElementById("siteSearchInput") ||
      document.querySelector('input[type="search"]') ||
      document.querySelector('input[placeholder*="Search" i]');

    let host = document.getElementById("home-links");
    if (!host) {
      const wrap = document.createElement("section");
      wrap.className = "home-quicklinks";
      wrap.setAttribute("aria-label", "Homepage quick buttons");

      host = document.createElement("div");
      host.id = "home-links";
      host.className = "home-links";
      wrap.appendChild(host);

      const insertBeforeNode =
        (searchInput && (searchInput.closest("section") || searchInput.closest("div"))) ||
        document.querySelector("main") ||
        document.body;

      insertBeforeNode.parentNode.insertBefore(wrap, insertBeforeNode);
    }

    // Add CSS once (no styles.css edit needed)
    if (!document.getElementById("home-quicklinks-style")) {
      const style = document.createElement("style");
      style.id = "home-quicklinks-style";
      style.textContent = `
        .home-quicklinks{max-width:1200px;margin:0 auto;padding:12px 16px 0;}
        .home-links{display:flex;flex-wrap:wrap;gap:10px;align-items:center;}
        .home-link-btn{display:inline-flex;align-items:center;gap:8px;padding:10px 14px;border-radius:12px;
          text-decoration:none;font-weight:600;box-shadow:0 6px 18px rgba(2,6,23,.08);}
        .home-link-btn i{font-size:14px;}
      `;
      document.head.appendChild(style);
    }

    // Load source-of-truth data
    let data = null;
    try {
      const r = await fetch("header_links.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const links = data && Array.isArray(data.home_links) ? data.home_links : [];
    host.innerHTML = "";

    links.forEach((lnk) => {
      const label = safe(lnk.label);
      const url = safe(lnk.url);
      const color = safe(lnk.color);
      const icon = safe(lnk.icon);

      const a = document.createElement("a");
      a.className = "home-link-btn";
      a.href = openInternal(url, label);
      a.style.background = color || "#eef2ff";
      a.innerHTML = `${icon ? `<i class="${icon}"></i>` : ""}<span>${label}</span>`;
      host.appendChild(a);
    });
  }

  function removeHomeMainPageCtaLinks() {
    const el = document.getElementById("mainCtaLinks");
    if (el) el.remove();
  }

  // ---------------------------
  // Category pages (Jobs / Admissions / More dropdown subpages)
  // ---------------------------
  async function initCategoryPage() {
    if (page !== "category.html") return;

    const params = new URLSearchParams(location.search || "");
    const group = safe(params.get("group")).toLowerCase();

    const titleEl = $("#categoryTitle") || $("h1") || $(".seo-block h1");
    const descEl = $("#categoryDesc") || $(".seo-block p");
    let gridEl = $("#categoryGrid") || $(".section-list");
    const emptyEl = $("#categoryEmpty");

    if (!gridEl) {
      const main = $("#main") || $("main") || document.body;
      const wrap = document.createElement("div");
      wrap.className = "section-list";
      main.appendChild(wrap);
      gridEl = wrap;
    }

    const groupMeta = {
      study: "Study wise jobs",
      popular: "Popular job categories",
      state: "State wise jobs",
      admit: "Admit card",
      result: "Results",
      more: "More",
    };

    const heading = groupMeta[group] || "Category";
    if (titleEl) titleEl.textContent = heading;
    if (descEl) descEl.textContent = `Browse ${heading} on Top Sarkari Jobs.`;

    let data = null;
    try {
      const r = await fetch("jobs.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    if (!data) return;

    const list = Array.isArray(data[group]) ? data[group] : [];
    gridEl.innerHTML = "";

    if (!list.length) {
      if (emptyEl) emptyEl.style.display = "block";
      return;
    }
    if (emptyEl) emptyEl.style.display = "none";

    list.forEach((it) => {
      const name = safe(it.name);
      const url = safe(it.url);

      const a = document.createElement("a");
      a.className = "section-link";
      a.href = openInternal(url, name);
      a.textContent = name || "Open";
      gridEl.appendChild(a);
    });
  }

  // ---------------------------
  // Tools page
  // ---------------------------
  async function initToolsPage() {
    if (page !== "tools.html") return;

    const host = document.getElementById("toolsGrid");
    if (!host) return;

    let data = null;
    try {
      const r = await fetch("tools.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    if (!data || !Array.isArray(data.tools)) return;

    host.innerHTML = "";

    data.tools.forEach((tool) => {
      const name = safe(tool.name);
      const url = safe(tool.url);
      const desc = safe(tool.desc);

      const a = document.createElement("a");
      a.className = "tool-card";
      a.href = openInternal(url, name);
      a.innerHTML = `
        <div class="tool-title">${name}</div>
        <div class="tool-desc">${desc}</div>
      `;
      host.appendChild(a);
    });
  }

  // ---------------------------
  // Supabase (helpdesk / CSC modal)
  // ---------------------------
  let __supabase = null;

  async function ensureSupabaseClient() {
    if (__supabase) return __supabase;

    const cfgRes = await fetch("config.json", { cache: "no-store" });
    const cfg = await cfgRes.json();

    if (!window.supabase || !window.supabase.createClient) {
      throw new Error("Supabase library not loaded");
    }

    __supabase = window.supabase.createClient(cfg.supabaseUrl, cfg.supabaseAnonKey);
    return __supabase;
  }

  function initCscModal() {
    const modal = document.getElementById("cscModal");
    if (!modal) return;

    const closeBtn = modal.querySelector("[data-close]");
    const overlay = modal.querySelector(".modal-overlay");

    const close = () => modal.classList.remove("open");

    if (closeBtn) closeBtn.addEventListener("click", close);
    if (overlay) overlay.addEventListener("click", close);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });
  }

  async function renderServicesPage() {
    if (page !== "govt-services.html") return;

    const host = document.getElementById("servicesGrid");
    if (!host) return;

    let data = null;
    try {
      const r = await fetch("services.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    if (!data || !Array.isArray(data.services)) return;

    host.innerHTML = "";

    data.services.forEach((svc) => {
      const name = safe(svc.name);
      const url = safe(svc.url);

      const card = document.createElement("a");
      card.className = "service-card";
      card.href = openInternal(url, name);
      card.innerHTML = `
        <div class="service-title">${name}</div>
        <div class="service-sub">Open official link</div>
      `;
      host.appendChild(card);
    });
  }

  // ---------------------------
  // Homepage Search (index.html only)
  // Binds to existing #siteSearchInput + #siteSearchBtn without changing layout
  // Redirects to view.html?q=...
  // ---------------------------
  function initHomepageSearch() {
    if (!(page === "index.html" || page === "")) return;

    const input = document.getElementById("siteSearchInput");
    const btn = document.getElementById("siteSearchBtn");
    if (!input || !btn) return;

    const run = () => {
      const q = safe(input.value);
      if (!q) {
        input.focus();
        return;
      }
      window.location.href = `view.html?q=${encodeURIComponent(q)}`;
    };

    // Prevent double-binding if script is re-evaluated
    if (!btn.dataset.boundHomeSearch) {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        run();
      });
      btn.dataset.boundHomeSearch = "1";
    }

    if (!input.dataset.boundHomeSearch) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          run();
        }
      });
      input.dataset.boundHomeSearch = "1";
    }
  }

  // ---------------------------
  // Boot
  // ---------------------------
  document.addEventListener("DOMContentLoaded", async () => {
    // ✅ NEW: this enables same homepage header/footer on pages that have:
    // <div id="site-header"></div> and <div id="site-footer"></div>
    await injectHeaderFooter();

    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    initFAQ();

    // Homepage content
    if (page === "index.html" || page === "") {
      await renderHomepageSections();
      await renderHomeQuickLinks();
      removeHomeMainPageCtaLinks();
      initHomepageSearch(); // ✅ ONLY NEW CALL (homepage search wiring)
    }
    // Category pages (Jobs/Admissions/More dropdown subpages)
    await initCategoryPage();

    // Tools page
    await initToolsPage();

    // CSC Services
    if (page === "govt-services.html") {
      ensureSupabaseClient().catch(() => {});
    }
    initCscModal();
    await renderServicesPage();
  });
})();
