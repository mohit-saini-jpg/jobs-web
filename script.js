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
  // ✅ category.html renderer using YOUR jobs.json format
  // ---------------------------
  async function initCategoryPage() {
    if (page !== "category.html") return;

    const params = new URLSearchParams(location.search || "");
    const group = safe(params.get("group")).toLowerCase();

    // Work even if your category.html ids are different:
    // - Prefer #categoryGrid
    // - Else use first .section-list
    // - Else create a container inside main
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
      study: { title: "Study wise jobs", desc: "" },
      popular: { title: "Popular job categories", desc: "" },
      state: { title: "State wise jobs", desc: "" },
      admissions: { title: "Admissions", desc: "" },
      "admit-result": { title: "Admit Card / Result / Answer Key / Syllabus", desc: "" },
      khabar: { title: "Latest Khabar", desc: "" },
      "study-material": { title: "Study Material & Top Courses", desc: "" },
    };

    if (titleEl) titleEl.textContent = (groupMeta[group]?.title || "Category");
    if (descEl && groupMeta[group]?.desc) descEl.textContent = groupMeta[group].desc;

    async function fetchJson(path) {
      const r = await fetch(path, { cache: "no-store" });
      if (!r.ok) throw new Error("Failed: " + path);
      return await r.json();
    }

    let data;
    try {
      data = await fetchJson("jobs.json");
    } catch (e) {
      // If jobs.json doesn't load, show nothing (no changes elsewhere)
      gridEl.innerHTML = "";
      if (emptyEl) emptyEl.hidden = false;
      return;
    }

    // YOUR FILE contains arrays with {title,...} headers and then {name,url,...} items :contentReference[oaicite:2]{index=2}
    const top = Array.isArray(data.top_jobs) ? data.top_jobs : [];
    const left = Array.isArray(data.left_jobs) ? data.left_jobs : [];
    const right = Array.isArray(data.right_jobs) ? data.right_jobs : [];

    const isHeader = (x) => x && typeof x === "object" && safe(x.title) && !safe(x.name);
    const isItem = (x) => x && typeof x === "object" && safe(x.name) && safe(x.url);

    function sliceBetween(arr, startTitleContains, endTitleContains) {
      const startIdx = arr.findIndex((x) => isHeader(x) && safe(x.title).toLowerCase().includes(startTitleContains));
      if (startIdx < 0) return [];
      let endIdx = arr.length;
      if (endTitleContains) {
        const ei = arr.findIndex((x, i) => i > startIdx && isHeader(x) && safe(x.title).toLowerCase().includes(endTitleContains));
        if (ei >= 0) endIdx = ei;
      }
      return arr.slice(startIdx + 1, endIdx).filter(isItem);
    }

    let items = [];

    // Jobs dropdown pages
    if (group === "study") {
      items = sliceBetween(top, "study wise", "popular");
    } else if (group === "popular") {
      items = sliceBetween(top, "popular", null);
    } else if (group === "state") {
      items = sliceBetween(left, "state wise", "admit");
    }

    // Admissions dropdown pages
    else if (group === "admit-result") {
      items = sliceBetween(left, "admit", null);
    } else if (group === "admissions") {
      items = sliceBetween(right, "admissions", "govt scheme");
    }

    // More dropdown pages
    else if (group === "khabar") {
      items = sliceBetween(right, "latest khabar", "study material");
    } else if (group === "study-material") {
      items = sliceBetween(right, "study material", "tools");
    }

    // Render (keep URLs exactly as in JSON)
    gridEl.innerHTML = "";
    if (!items.length) {
      if (emptyEl) emptyEl.hidden = false;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;

    items.forEach((it) => {
      const name = safe(it.name);
      const url = safe(it.url);
      const external = it.external === true;

      const a = document.createElement("a");
      a.className = "section-link";
      a.href = url; // ✅ EXACT URL FROM jobs.json
      if (external) {
        a.target = "_blank";
        a.rel = "noopener";
      }
      a.innerHTML = `
        <div class="t">${name}</div>
        <div class="d">Open official link</div>
      `;
      gridEl.appendChild(a);
    });
  }

  // Boot
  document.addEventListener("DOMContentLoaded", async () => {
    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    initFAQ();

    // ✅ Restore dropdown subpages content from jobs.json
    await initCategoryPage();
  });
})();
