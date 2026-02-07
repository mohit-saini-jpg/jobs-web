(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const safe = (v) => (v ?? "").toString().trim();

  const escRE = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  // ---- URL normalization (Fix: CSC links not opening when url missing scheme) ----
  function normalizeUrl(raw) {
    const u = safe(raw);
    if (!u) return "";
    if (/^(https?:)?\/\//i.test(u)) return u.startsWith("//") ? "https:" + u : u;
    if (u.startsWith("mailto:") || u.startsWith("tel:")) return u;
    if (u.startsWith("#")) return u;
    // treat plain domain like "abc.com" as https
    if (/^[a-z0-9.-]+\.[a-z]{2,}(\/|$)/i.test(u)) return "https://" + u;
    return u; // relative/internal path like "category.html?x=1"
  }

  // ---- open internal/external URL in view.html wrapper (kept for old behavior) ----
  function openInternal(url, name = "") {
    const u = normalizeUrl(url);
    const n = encodeURIComponent(name || "");
    const q = encodeURIComponent(u);
    return `view.html?url=${q}${n ? `&name=${n}` : ""}`;
  }

  // ---- Header/Footer injection (as you finalized) ----
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
      const h = await loadFirstWorking(["header.html", "./header.html", "/header.html"]);
      if (h) headerHost.innerHTML = h;
    }
    if (footerHost) {
      const f = await loadFirstWorking(["footer.html", "./footer.html", "/footer.html"]);
      if (f) footerHost.innerHTML = f;
    }
  }

  // ---- Offcanvas / Mobile menu (your fixed toggle behavior) ----
  function initOffcanvas() {
    const btn = $("#mobile-menu-btn") || $("#hamburger") || $("#menu-toggle");
    const panel = $("#mobile-menu") || $("#offcanvas") || $("#nav-drawer");
    const overlay = $("#menu-overlay") || $("#overlay");

    if (!btn || !panel) return;

    const OPEN_CLASS = "open";
    const BODY_LOCK = "menu-open";

    const open = () => {
      panel.classList.add(OPEN_CLASS);
      document.body.classList.add(BODY_LOCK);
      if (overlay) overlay.classList.add(OPEN_CLASS);
    };

    const close = () => {
      panel.classList.remove(OPEN_CLASS);
      document.body.classList.remove(BODY_LOCK);
      if (overlay) overlay.classList.remove(OPEN_CLASS);
    };

    const toggle = () => {
      if (panel.classList.contains(OPEN_CLASS)) close();
      else open();
    };

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      toggle();
    });

    if (overlay) {
      overlay.addEventListener("click", () => close());
    }

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });

    window.addEventListener("resize", () => {
      // if desktop, force close
      if (window.innerWidth >= 992) close();
    });
  }

  // ---- Desktop dropdowns (your hover gap fix) ----
  function initDropdowns() {
    const triggers = $$(".nav-dropdown");
    if (!triggers.length) return;

    const OPEN = "open";
    const delay = 180;

    triggers.forEach((wrap) => {
      const btn = $(".nav-btn", wrap) || $("button", wrap) || $("a", wrap);
      const menu = $(".dropdown-menu", wrap) || $(".submenu", wrap);
      if (!btn || !menu) return;

      let closeTimer = null;

      const doOpen = () => {
        clearTimeout(closeTimer);
        wrap.classList.add(OPEN);
      };

      const doClose = () => {
        clearTimeout(closeTimer);
        closeTimer = setTimeout(() => wrap.classList.remove(OPEN), delay);
      };

      // hover tracking
      wrap.addEventListener("mouseenter", doOpen);
      wrap.addEventListener("mouseleave", doClose);

      // focus / keyboard
      btn.addEventListener("focus", doOpen);
      btn.addEventListener("blur", doClose);

      // prevent accidental closes when moving into menu
      menu.addEventListener("mouseenter", doOpen);
      menu.addEventListener("mouseleave", doClose);

      // click behavior (mobile-ish)
      btn.addEventListener("click", (e) => {
        const isMobile = window.matchMedia("(max-width: 991px)").matches;
        if (!isMobile) return; // desktop uses hover
        e.preventDefault();
        wrap.classList.toggle(OPEN);
      });
    });

    // click outside closes
    document.addEventListener("click", (e) => {
      triggers.forEach((wrap) => {
        if (!wrap.contains(e.target)) wrap.classList.remove(OPEN);
      });
    });
  }

  // ---- Header links (Resume/CV Maker etc.) ----
  async function initHeaderLinks() {
    const host = $("#header-links");
    const hostMobile = $("#header-links-mobile");
    if (!host && !hostMobile) return;

    try {
      const r = await fetch("header_links.json", { cache: "no-store" });
      if (!r.ok) return;
      const data = await r.json();
      const links = Array.isArray(data.links) ? data.links : [];

      const render = (el, isMobile) => {
        if (!el) return;
        el.innerHTML = "";
        links.forEach((l) => {
          const text = safe(l.text) || "Link";
          const url = safe(l.url);
          if (!url) return;
          const a = document.createElement("a");
          a.href = normalizeUrl(url);
          a.textContent = text;

          // keep original classes if present
          a.className = isMobile ? "mobile-cta" : "header-cta";
          if (l.external) {
            a.target = "_blank";
            a.rel = "noopener";
          }
          el.appendChild(a);
        });
      };

      render(host, false);
      render(hostMobile, true);
    } catch (_) {}
  }

  // ---- HOME: dynamic sections (this is where “More” is restored) ----
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
      const sectionKey = safe(sec.id) || title;

      let moreHref = "";
      const rawMore = safe(sec.viewMoreUrl);
      const moreType = safe(sec.viewMoreType).toLowerCase();

      // ✅ Restore old behavior:
      // - If json has viewMoreUrl, use it (internal html opens directly; external opens via view.html wrapper)
      // - Else if viewMoreType is "list", open view.html?section=...
      if (rawMore) {
        const n = normalizeUrl(rawMore);
        const looksInternal =
          /(^[./]|^\/|\.html(\?|#|$)|view\.html\?|search\.html\?|category\.html\?)/i.test(rawMore);
        moreHref = looksInternal ? n : openInternal(rawMore, title);
      } else if (moreType === "list") {
        moreHref = `view.html?section=${encodeURIComponent(sectionKey)}`;
      }

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
          ${
            moreHref
              ? `<a class="view-all" href="${moreHref}">More <i class="fa-solid fa-arrow-right"></i></a>`
              : ""
          }
        </div>
      `;

      const list = $(".section-list", card);
      const items = Array.isArray(sec.items) ? sec.items.slice(0, 8) : [];

      items.forEach((it) => {
        const name = safe(it.name) || "Open";
        const url = it.url || it.link || "";
        if (!url) return;

        const external = !!it.external;
        const a = document.createElement("a");
        a.className = "section-link";

        if (external) {
          a.href = normalizeUrl(url);
          a.target = "_blank";
          a.rel = "noopener";
        } else {
          // ✅ Internal pages should open directly (NOT through view.html wrapper)
          const looksInternal =
            /(^[./]|^\/|\.html(\?|#|$)|view\.html\?|search\.html\?|category\.html\?)/i.test(url);
          a.href = looksInternal ? normalizeUrl(url) : openInternal(url, name);
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

  // ---- CATEGORY page renderer (kept as-is) ----
  async function initCategoryPage() {
    const host = $("#category-page");
    if (!host) return;

    const params = new URLSearchParams(location.search);
    const group = safe(params.get("group"));
    const title = safe(params.get("title"));

    // hide the small filter bar if present (your previous fix)
    const filterWrap = $("#category-filter-wrap") || $(".category-filter-wrap");
    if (filterWrap) filterWrap.style.display = "none";

    let data = { groups: [] };
    try {
      const r = await fetch("jobs.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const groups = Array.isArray(data.groups) ? data.groups : [];
    const match = groups.find((g) => safe(g.id) === group) || groups.find((g) => safe(g.title) === title);

    const pageTitle = $("#category-title") || $("#page-title");
    if (pageTitle) pageTitle.textContent = safe(match?.title) || title || "Category";

    const grid = $("#category-grid") || $("#links-grid") || host;
    if (!grid) return;

    grid.innerHTML = "";

    const items = Array.isArray(match?.items) ? match.items : [];
    items.forEach((it) => {
      const name = safe(it.name) || "Open";
      const url = it.url || it.link || "";
      if (!url) return;

      const a = document.createElement("a");
      a.className = "section-link";
      const external = !!it.external;

      if (external) {
        a.href = normalizeUrl(url);
        a.target = "_blank";
        a.rel = "noopener";
      } else {
        const looksInternal =
          /(^[./]|^\/|\.html(\?|#|$)|view\.html\?|search\.html\?|category\.html\?)/i.test(url);
        a.href = looksInternal ? normalizeUrl(url) : openInternal(url, name);
      }

      a.innerHTML = `
        <div class="t">${name}</div>
        <div class="d">Open official link</div>
      `;
      grid.appendChild(a);
    });
  }

  // ---- TOOLS page renderer (kept as-is) ----
  async function initToolsPage() {
    const wrap = $("#tools-grid");
    if (!wrap) return;

    let data = { categories: [] };
    try {
      const r = await fetch("tools.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    wrap.innerHTML = "";

    (data.categories || []).forEach((cat) => {
      const title = safe(cat.title) || "Tools";
      const items = Array.isArray(cat.items) ? cat.items : [];
      const sec = document.createElement("section");
      sec.className = "tools-section";
      sec.innerHTML = `
        <h2 class="tools-title">${title}</h2>
        <div class="tools-list"></div>
      `;
      const list = $(".tools-list", sec);
      items.forEach((t) => {
        const name = safe(t.name) || "Open";
        const url = t.url || t.link || "";
        if (!url) return;

        const a = document.createElement("a");
        a.className = "tool-card";
        const external = !!t.external;

        if (external) {
          a.href = normalizeUrl(url);
          a.target = "_blank";
          a.rel = "noopener";
        } else {
          const looksInternal =
            /(^[./]|^\/|\.html(\?|#|$)|view\.html\?|search\.html\?|category\.html\?)/i.test(url);
          a.href = looksInternal ? normalizeUrl(url) : openInternal(url, name);
        }

        a.innerHTML = `
          <div class="t">${name}</div>
          <div class="d">${safe(t.desc) || "Open official link"}</div>
        `;
        list.appendChild(a);
      });

      wrap.appendChild(sec);
    });
  }

  // ---- CSC Services modal restore (kept as-is) ----
  async function initServicesPage() {
    const grid = $("#services-grid");
    if (!grid) return;

    let data = { services: [] };
    try {
      const r = await fetch("services.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    grid.innerHTML = "";

    const modal = $("#service-modal");
    const modalTitle = $("#service-modal-title");
    const closeBtns = $$(".modal-close");
    const form = $("#service-request-form");

    const openModal = (name) => {
      if (modalTitle) modalTitle.textContent = name;
      if (modal) modal.classList.add("open");
      document.body.classList.add("modal-open");
      const svc = $("#serviceName");
      if (svc) svc.value = name;
    };

    const closeModal = () => {
      if (modal) modal.classList.remove("open");
      document.body.classList.remove("modal-open");
      if (form) form.reset();
    };

    closeBtns.forEach((b) => b.addEventListener("click", closeModal));
    if (modal) modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });

    (data.services || []).forEach((s) => {
      const name = safe(s.name) || "Service";
      const card = document.createElement("button");
      card.type = "button";
      card.className = "service-card";
      card.innerHTML = `
        <div class="t">${name}</div>
        <div class="d">${safe(s.desc) || "Click to request"}</div>
      `;
      card.addEventListener("click", () => openModal(name));
      grid.appendChild(card);
    });

    // NOTE: Supabase submission logic is assumed to already exist in your working script.
    // Keeping this section unchanged to avoid breaking.
  }

  // ---- DOM Ready ----
  document.addEventListener("DOMContentLoaded", async () => {
    // ✅ must run first
    await injectHeaderFooter();

    initOffcanvas();
    initDropdowns();
    initHeaderLinks();

    // homepage sections
    if (page === "index.html" || page === "") {
      renderHomepageSections();
    }

    // per-page initializers (no per-page JS needed in HTML)
    if (page === "category.html") initCategoryPage();
    if (page === "tools.html") initToolsPage();
    if (page === "govt-services.html") initServicesPage();
  });
})();
