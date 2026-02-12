(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const safe = (v) => (v ?? "").toString().trim();

  function normalizeUrl(raw) {
    const s = safe(raw);
    if (!s) return "";
    if (/^(https?:)?\/\//i.test(s) || /^(mailto:|tel:)/i.test(s)) return s;
    if (s.startsWith("#") || s.startsWith("?")) return s;
    if (s.startsWith("/") || s.endsWith(".html") || s.startsWith("./") || s.startsWith("../")) return s;
    return "https://" + s.replace(/^\/+/, "");
  }

  // ✅ HELPER: Block "Main Home Page" garbage link
  function isGarbageLink(item) {
    const text = (item.name || item.title || "").toLowerCase();
    const badPhrases = [
      "website का main home page",
      "main home page खोलने",
      "website ka main home page"
    ];
    return badPhrases.some(p => text.includes(p));
  }

  function openInternal(url, name) {
    const u = normalizeUrl(url);
    return `view.html?url=${encodeURIComponent(u)}&name=${encodeURIComponent(name)}`;
  }

  // Back button logic
  window.goBack = () => {
    if (window.history.length > 1) window.history.back();
    else window.location.href = "index.html";
  };

  // Inject Header/Footer
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

  // Mobile menu
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
      if (e.target.closest("a")) close();
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 980) close();
    });
    window.__closeMenu = close;
  }

  // Dropdowns
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
      dds.forEach((dd) => { clearTimer(dd); setOpen(dd, false); });
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
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest("[data-dd]")) closeAll();
    });
  }

  // FAQ
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

  // Homepage Sections (Updates)
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

      const sectionKey = safe(sec.id) || safe(sec.title);
      let moreHref = "";
      if (safe(sec.viewMoreUrl)) {
        moreHref = openInternal(sec.viewMoreUrl, title);
      } else if (safe(sec.viewMoreType).toLowerCase() === "list" && sectionKey) {
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
          ${moreHref ? `<a class="view-all" href="${moreHref}">More <i class="fa-solid fa-arrow-right"></i></a>` : ""}
        </div>
      `;

      const list = $(".section-list", card);
      // ✅ FILTER: Remove "Main Home Page" link here
      const items = Array.isArray(sec.items) 
        ? sec.items.filter(i => !isGarbageLink(i)).slice(0, 8) 
        : [];

      items.forEach((it) => {
        const name = safe(it.name) || "Open";
        const url = it.url || it.link || "";
        if (!url) return;

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

  // Homepage Headlines
  async function renderHomeQuickLinks() {
    if (!(page === "index.html" || page === "")) return;
    
    // Insert location
    const searchInput = $("#siteSearchInput");
    let host = $("#home-links");
    
    if (!host) {
      const wrap = document.createElement("section");
      wrap.className = "home-quicklinks";
      host = document.createElement("div");
      host.id = "home-links";
      host.className = "home-links";
      wrap.appendChild(host);

      // Try to insert above search, otherwise at top of main
      const target = (searchInput && searchInput.closest(".container")) || $("main") || document.body;
      target.parentNode.insertBefore(wrap, target);
    }

    // Styles
    if (!document.getElementById("home-quicklinks-style")) {
      const style = document.createElement("style");
      style.id = "home-quicklinks-style";
      style.textContent = `
        .home-quicklinks{width:min(1180px, calc(100% - 32px));margin:0 auto;padding:12px 0 0;}
        .home-links{display:flex;flex-wrap:wrap;gap:10px;align-items:center;}
        .home-link-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:10px 14px;border-radius:12px;color:#fff;font-weight:800;text-decoration:none;line-height:1;box-shadow:0 8px 18px rgba(2,6,23,.10);border:1px solid rgba(255,255,255,.15);white-space:nowrap;}
        .home-link-btn:hover{filter:brightness(.95);}
        .home-link-btn:active{transform:translateY(1px);}
      `;
      document.head.appendChild(style);
    }

    let data = null;
    try {
      const r = await fetch("header_links.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const links = Array.isArray(data?.home_links) ? data.home_links : [];
    if (!links.length) return;

    const colorMap = {
      "bg-red-600": "#dc2626", "bg-slate-600": "#475569", "bg-amber-600": "#0ea5a4",
      "bg-zinc-400": "#9ca3af", "bg-green-600": "#16a34a", "bg-pink-500": "#ec4899",
      "bg-yellow-600": "#ca8a04", "bg-red-500": "#ef4444",
    };

    host.innerHTML = "";
    links.forEach((l) => {
      const name = safe(l?.name);
      const url = safe(l?.url || l?.link);
      if (!name || !url) return;
      
      const a = document.createElement("a");
      a.className = "home-link-btn";
      a.href = normalizeUrl(url);
      if (l?.external) { a.target = "_blank"; a.rel = "noopener"; }
      a.style.background = colorMap[safe(l?.color)] || "#0ea5e9";
      
      const icon = safe(l?.icon);
      if (icon) a.innerHTML = `<i class="${icon}"></i><span>${name}</span>`;
      else a.textContent = name;
      host.appendChild(a);
    });
  }

  // Category Pages
  async function initCategoryPage() {
    if (page !== "category.html") return;
    const params = new URLSearchParams(location.search || "");
    const group = safe(params.get("group")).toLowerCase();

    const titleEl = $("#categoryTitle") || $("h1");
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
      study: "Study wise jobs", popular: "Popular job categories", state: "State wise jobs",
      admissions: "Admissions", "admit-result": "Admit Card / Result",
      khabar: "Latest Khabar", "study-material": "Study Material & Top Courses",
    };
    if (titleEl) titleEl.textContent = groupMeta[group] || "Category";

    let data;
    try {
      const r = await fetch("jobs.json", { cache: "no-store" });
      if(!r.ok) throw new Error();
      data = await r.json();
    } catch (_) {
      gridEl.innerHTML = "";
      return;
    }

    const top = Array.isArray(data.top_jobs) ? data.top_jobs : [];
    const left = Array.isArray(data.left_jobs) ? data.left_jobs : [];
    const right = Array.isArray(data.right_jobs) ? data.right_jobs : [];

    const isHeader = (x) => x && typeof x === "object" && safe(x.title) && !safe(x.name);
    const isItem = (x) => x && typeof x === "object" && safe(x.name) && safe(x.url);

    function sliceBetween(arr, startIncludes, endIncludes) {
      const startIdx = arr.findIndex(x => isHeader(x) && safe(x.title).toLowerCase().includes(startIncludes));
      if (startIdx < 0) return [];
      let endIdx = arr.length;
      if (endIncludes) {
        const ei = arr.findIndex((x, i) => i > startIdx && isHeader(x) && safe(x.title).toLowerCase().includes(endIncludes));
        if (ei >= 0) endIdx = ei;
      }
      return arr.slice(startIdx + 1, endIdx).filter(isItem);
    }

    let items = [];
    if (group === "study") items = sliceBetween(top, "study wise", "popular");
    else if (group === "popular") items = sliceBetween(top, "popular", null);
    else if (group === "state") items = sliceBetween(left, "state wise", "admit");
    else if (group === "admit-result") items = sliceBetween(left, "admit", null);
    else if (group === "admissions") items = sliceBetween(right, "admissions", "govt scheme");
    else if (group === "khabar") items = sliceBetween(right, "latest khabar", "study material");
    else if (group === "study-material") items = sliceBetween(right, "study material", "tools");

    // ✅ FILTER: Remove "Main Home Page" link here too
    items = items.filter(i => !isGarbageLink(i));

    gridEl.innerHTML = "";
    items.forEach((it) => {
      const a = document.createElement("a");
      a.className = "section-link";
      a.href = safe(it.url);
      if (it.external) { a.target = "_blank"; a.rel = "noopener"; }
      a.innerHTML = `<div class="t">${safe(it.name)}</div><div class="d">Open official link</div>`;
      gridEl.appendChild(a);
    });
  }

  // Tools Page
  async function initToolsPage() {
    if (page !== "tools.html") return;
    const toolsGrid = $("#tools-grid");
    if (!toolsGrid) return;
    
    let data = null;
    try {
      const r = await fetch("tools.json");
      data = await r.json();
    } catch(_) {}
    
    // Logic for tools page handled by HTML onClick usually, but if needed we can expand.
  }

  // CSC
  function initCscModal() {
    const modal = $("#cscModal");
    const overlay = $("#cscModalOverlay");
    const closeBtn = $("#cscModalClose");
    const form = $("#cscRequestForm");
    if (!modal || !overlay || !closeBtn || !form) return;
    
    // ... (CSC modal logic remains standard)
    const close = () => {
      modal.hidden = true;
      overlay.hidden = true;
      document.body.style.overflow = "";
    };
    overlay.addEventListener("click", close);
    closeBtn.addEventListener("click", close);
    window.__openCscModal = (service) => {
      if($("#cscServiceName")) $("#cscServiceName").textContent = service.name || "Service";
      modal.hidden = false;
      overlay.hidden = false;
      document.body.style.overflow = "hidden";
    };
  }

  // ✅ GLOBAL LIVE SEARCH
  // Works on homepage AND view.html (if search bar exists)
  async function initGlobalLiveSearch() {
    // 1. Find the input. It might be on index.html OR view.html
    const input = document.getElementById("siteSearchInput");
    const resultsWrap = document.getElementById("searchResults");
    
    // If we are on a page without a search bar, stop.
    if (!input || !resultsWrap) return;

    let searchData = [];
    try {
      const [dyn, jobs, tools, services] = await Promise.all([
        fetch("dynamic-sections.json").then(r => r.json()).catch(() => ({})),
        fetch("jobs.json").then(r => r.json()).catch(() => ({})),
        fetch("tools.json").then(r => r.json()).catch(() => ({})),
        fetch("services.json").then(r => r.json()).catch(() => ({}))
      ]);

      const push = (name, url, src) => {
        if(!name || !url) return;
        // ✅ FILTER: Exclude garbage link from search
        if (isGarbageLink({name})) return;
        searchData.push({ name: name.trim(), url: url.trim(), src });
      };

      if (dyn.sections) {
        dyn.sections.forEach(s => s.items?.forEach(i => push(i.name || i.title, i.url || i.link, s.title || "Update")));
      }
      [jobs.top_jobs, jobs.left_jobs, jobs.right_jobs].forEach(arr => {
        arr?.forEach(i => push(i.name || i.title, i.url || i.link, "Category"));
      });
      if (tools) {
        Object.keys(tools).forEach(k => {
          if(Array.isArray(tools[k])) tools[k].forEach(t => push(t.name, t.url, "Tool"));
        });
      }
      if (services.services) {
        services.services.forEach(s => push(s.name, "govt-services.html", "CSC Service"));
      }
    } catch (e) {}

    const performSearch = () => {
      const query = input.value.toLowerCase().trim();
      if (query.length < 2) {
        resultsWrap.innerHTML = "";
        resultsWrap.style.display = "none";
        return;
      }

      const tokens = query.split(/\s+/).filter(t => t.length);
      const matches = searchData.filter(item => {
        const hay = (item.name + " " + item.src).toLowerCase();
        return tokens.every(t => hay.includes(t));
      }).slice(0, 10);

      resultsWrap.innerHTML = "";
      if (matches.length > 0) {
        resultsWrap.style.display = "block";
        matches.forEach(m => {
          let href = m.url;
          const isExternal = m.url.startsWith("http") && !m.url.includes(location.hostname);
          if (isExternal || (!m.url.endsWith(".html") && !m.url.startsWith("#"))) {
             href = openInternal(m.url, m.name);
          }
          const a = document.createElement("a");
          a.className = "search-result-item";
          a.href = href;
          a.innerHTML = `<div class="result-name">${m.name}</div><div class="result-meta">${m.src}</div>`;
          resultsWrap.appendChild(a);
        });
      } else {
        resultsWrap.style.display = "block";
        resultsWrap.innerHTML = `<div class="search-no-results">No matches found.</div>`;
      }
    };

    input.addEventListener("input", performSearch);
    input.addEventListener("focus", () => { if(input.value.length >= 2) resultsWrap.style.display="block"; });
    
    document.addEventListener("click", (e) => {
      if (!input.contains(e.target) && !resultsWrap.contains(e.target)) {
        resultsWrap.style.display = "none";
      }
    });
  }

  // Boot
  document.addEventListener("DOMContentLoaded", async () => {
    await injectHeaderFooter();
    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    initFAQ();

    if (page === "index.html" || page === "") {
      await renderHomepageSections();
      await renderHomeQuickLinks();
    }

    await initCategoryPage();
    await initToolsPage();
    initCscModal();
    
    // Initialize Search everywhere (it checks for ID existence internally)
    await initGlobalLiveSearch();
  });
})();
