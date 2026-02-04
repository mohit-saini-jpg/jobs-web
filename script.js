(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const safe = (v) => (v ?? "").toString().trim();
  const escRE = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  // Fix URLs that are missing scheme (https://)
  function normalizeExternalUrl(input) {
    const url = safe(input);
    if (!url) return "";

    // already has scheme like https:, http:, mailto:, tel:, etc.
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(url)) return url;

    // protocol-relative //example.com
    if (url.startsWith("//")) return "https:" + url;

    // www.example.com
    if (/^www\./i.test(url)) return "https://" + url;

    // looks like a domain (example.com/...)
    if (/^[\w-]+\.[\w.-]+/.test(url)) return "https://" + url;

    // otherwise leave as-is (could be relative file)
    return url;
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
    const footerSocial = $("#footer-social-links");

    const links = Array.isArray(data.header_links) ? data.header_links : [];
    const socials = Array.isArray(data.social_links) ? data.social_links : [];

    if (desktop) {
      desktop.innerHTML = "";
      links.forEach((l) => {
        const a = document.createElement("a");
        a.className = "nav-link";
        a.href = normalizeExternalUrl(l.link || l.url || "#");
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
        a.href = normalizeExternalUrl(l.link || l.url || "#");
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
        a.href = normalizeExternalUrl(s.url || "#");
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = s.name || "Social";
        footerSocial.appendChild(a);
      });
    }
  }

  // -------------------------
  // Offcanvas menu (FIX: toggle + never stuck)
  // -------------------------
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
      document.documentElement.style.overflow = "";
    };

    const open = () => {
      menu.hidden = false;
      overlay.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
      document.documentElement.style.overflow = "hidden";
    };

    // ✅ Toggle (this is what your current script DOESN’T do)
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const isOpen = btn.getAttribute("aria-expanded") === "true" && !menu.hidden;
      if (isOpen) close();
      else open();
    });

    closeBtn.addEventListener("click", (e) => {
      e.preventDefault();
      close();
    });

    overlay.addEventListener("click", close);

    // close on any menu link click
    menu.addEventListener("click", (e) => {
      const a = e.target.closest("a");
      if (a) close();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });

    // Safety: close on resize back to desktop
    window.addEventListener("resize", () => {
      if (window.innerWidth > 980) close();
    });

    // Safety: prevents “scroll locked” stuck state on navigation
    window.addEventListener("pagehide", close);

    window.__closeMenu = close;
  }

  // -------------------------
  // Desktop dropdowns
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
      });
    };

    dds.forEach((dd) => {
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

      dd.addEventListener("mouseenter", () => {
        if (window.matchMedia("(hover:hover)").matches) {
          closeAll();
          menu.classList.add("open");
          btn.setAttribute("aria-expanded", "true");
        }
      });

      dd.addEventListener("mouseleave", () => {
        if (window.matchMedia("(hover:hover)").matches) {
          menu.classList.remove("open");
          btn.setAttribute("aria-expanded", "false");
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
  // View helper
  // -------------------------
  function openInternal(url, name) {
    return `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`;
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
        const url = it.url || it.link || "";
        if (!url) return;
        const external = !!it.external;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = external ? normalizeExternalUrl(url) : openInternal(url, name);
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
  // CSC Services page (govt-services.html)  ✅ FIXED LINKS
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
      const rawUrl = s.url || s.link || "";
      const url = normalizeExternalUrl(rawUrl);

      if (!name) return;

      const a = document.createElement("a");
      a.className = "section-link";
      a.href = url || "#";
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
  // Tools page (tools.html)
  // -------------------------
  async function renderToolsPage() {
    if (page !== "tools.html") return;

    const grid = $("#toolsGrid");
    if (!grid) return;

    let data = null;
    try {
      const r = await fetch("tools.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    grid.innerHTML = "";
    grid.classList.add("cat-grid");

    const buckets = [
      { key: "image", title: "Image Tools", color: "#0ea5e9" },
      { key: "pdf", title: "PDF Tools", color: "#4f46e5" },
      { key: "video", title: "Video Tools", color: "#db2777" }
    ];

    let any = false;

    buckets.forEach((b) => {
      const items = data && Array.isArray(data[b.key]) ? data[b.key] : [];
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
        const rawUrl = it.url || it.link || "";
        if (!name || !rawUrl) return;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = it.external ? normalizeExternalUrl(rawUrl) : openInternal(rawUrl, name);
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

  // -------------------------
  // Boot
  // -------------------------
  document.addEventListener("DOMContentLoaded", async () => {
    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    initFAQ();

    if (page === "index.html" || page === "") {
      await renderHomepageSections();
    }

    await renderServicesPage();
    await renderToolsPage();
  });
})();
