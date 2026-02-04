(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  const safe = (v) => (v ?? "").toString().trim();

  // Fix URLs missing scheme (https://)
  function normalizeExternalUrl(input) {
    const url = safe(input);
    if (!url) return "";

    // already has a scheme: https:, http:, mailto:, tel:, etc.
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(url)) return url;

    // protocol-relative //example.com
    if (url.startsWith("//")) return "https:" + url;

    // www.example.com
    if (/^www\./i.test(url)) return "https://" + url;

    // looks like a domain
    if (/^[\w-]+\.[\w.-]+/.test(url)) return "https://" + url;

    // fallback (could be relative file)
    return url;
  }

  // -------------------------
  // Header/footer links
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
  // Offcanvas menu (FIX: TOGGLE, not stuck)
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

    // ✅ Toggle: click hamburger again closes the menu
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

    window.addEventListener("resize", () => {
      if (window.innerWidth > 980) close();
    });

    window.addEventListener("pagehide", close);
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
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest("[data-dd]")) closeAll();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeAll();
    });
  }

  // -------------------------
  // CSC Services page (FIX LINKS)
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
  // Boot
  // -------------------------
  document.addEventListener("DOMContentLoaded", async () => {
    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    await renderServicesPage();
  });
})();
