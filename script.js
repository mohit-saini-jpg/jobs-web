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
    if (/^[a-z0-9.-]+\.[a-z]{2,}(\/|$)/i.test(s)) return "https://" + s;
    return s;
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

  // ---------------------------
  // Inject header/footer
  // ---------------------------
  async function injectHeaderFooter() {
    const headerHost = document.getElementById("site-header");
    const footerHost = document.getElementById("site-footer");

    async function fetchText(path) {
      const res = await fetch(path, { cache: "no-store" });
      if (!res.ok) throw new Error(`Failed to load ${path}`);
      return await res.text();
    }

    if (headerHost) {
      headerHost.innerHTML = await fetchText("header.html");
    }
    if (footerHost) {
      footerHost.innerHTML = await fetchText("footer.html");
    }
  }

  // ---------------------------
  // Header links loader (header_links.json)
  // ---------------------------
  async function loadHeaderLinks() {
    const res = await fetch("header_links.json", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json().catch(() => null);
    if (!data) return;

    // Header dropdowns already exist in header.html and are stable,
    // so we only ensure data is available for homepage quicklinks.
    window.__HEADER_LINKS__ = data;
  }

  // ---------------------------
  // Offcanvas (mobile nav)
  // ---------------------------
  function initOffcanvas() {
    const openBtn = document.querySelector("[data-offcanvas-open]");
    const closeBtn = document.querySelector("[data-offcanvas-close]");
    const panel = document.querySelector("[data-offcanvas]");
    if (!panel) return;

    const open = () => panel.classList.add("open");
    const close = () => panel.classList.remove("open");

    if (openBtn) openBtn.addEventListener("click", open);
    if (closeBtn) closeBtn.addEventListener("click", close);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });
  }

  // ---------------------------
  // Dropdowns
  // ---------------------------
  function initDropdowns() {
    const toggles = $$("[data-dropdown-toggle]");
    toggles.forEach((btn) => {
      const menuId = btn.getAttribute("data-dropdown-toggle");
      const menu = document.getElementById(menuId);
      if (!menu) return;

      const closeAll = () => {
        $$("[data-dropdown-menu]").forEach((m) => m.classList.remove("open"));
      };

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const isOpen = menu.classList.contains("open");
        closeAll();
        if (!isOpen) menu.classList.add("open");
      });

      document.addEventListener("click", (e) => {
        if (!menu.contains(e.target) && !btn.contains(e.target)) {
          menu.classList.remove("open");
        }
      });
    });
  }

  // ---------------------------
  // FAQ toggle (homepage + result page style)
  // ---------------------------
  function initFAQ() {
    $$(".faq-item button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const item = btn.closest(".faq-item");
        if (!item) return;
        item.classList.toggle("open");
      });
    });
  }

  // ---------------------------
  // Homepage sections (dynamic-sections.json)
  // ---------------------------
  async function renderHomepageSections() {
    if (!(page === "index.html" || page === "")) return;

    const host = document.getElementById("dynamic-sections");
    if (!host) return;

    const res = await fetch("dynamic-sections.json", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json().catch(() => null);
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
      // ✅ More links go to view.html?section=...
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
    let data = window.__HEADER_LINKS__;
    if (!data) {
      const res = await fetch("header_links.json", { cache: "no-store" });
      if (!res.ok) return;
      data = await res.json().catch(() => null);
      if (!data) return;
      window.__HEADER_LINKS__ = data;
    }

    const links = Array.isArray(data.home_links) ? data.home_links : [];
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

  // ---------------------------
  // Remove homepage CTA links (legacy)
  // ---------------------------
  function removeHomeMainPageCtaLinks() {
    // This was part of earlier experiments; keep as-is (working).
    // No-op unless elements exist.
    const el = document.getElementById("mainCtaLinks");
    if (el) el.remove();
  }

  // ---------------------------
  // Category pages (Jobs / Admissions / More dropdown subpages)
  // Uses YOUR jobs.json structure and keeps URLs exactly as-is
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

    const res = await fetch("jobs.json", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json().catch(() => null);
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

    const res = await fetch("tools.json", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json().catch(() => null);
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

    // Expect global supabase from CDN (already included in pages that need it)
    if (!window.supabase || !window.supabase.createClient) {
      throw new Error("Supabase library not loaded");
    }

    __supabase = window.supabase.createClient(cfg.supabaseUrl, cfg.supabaseAnonKey);
    return __supabase;
  }

  // CSC modal (govt-services) – keep existing working behavior
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

  // Render CSC services page (govt-services.html) – keep existing working behavior
  async function renderServicesPage() {
    if (page !== "govt-services.html") return;

    const host = document.getElementById("servicesGrid");
    if (!host) return;

    const res = await fetch("services.json", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json().catch(() => null);
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

    // prevent double-binding
    if (!btn.dataset.boundSearch) {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        run();
      });
      btn.dataset.boundSearch = "1";
    }

    if (!input.dataset.boundSearch) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          run();
        }
      });
      input.dataset.boundSearch = "1";
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
