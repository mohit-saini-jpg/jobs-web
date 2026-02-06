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

  // ✅ Inject same homepage header/footer everywhere
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
  // ✅ NEW: Remove/hide header search UI on ALL pages except homepage
  // ---------------------------
  function removeHeaderSearchEverywhereExceptHome() {
    const isHome = page === "index.html" || page === "";
    if (isHome) return;

    // 1) Remove "Search" nav links (desktop + mobile) that point to search.html
    const anchors = $$('a[href]');
    anchors.forEach((a) => {
      const href = safe(a.getAttribute("href")).toLowerCase();
      if (!href) return;

      // remove only the HEADER search UI (not random content links)
      // heuristic: points to search.html or contains "search.html"
      if (href.includes("search.html")) {
        // If it's in a nav/header area, remove it
        const inHeader =
          !!a.closest("header") ||
          !!a.closest("nav") ||
          !!a.closest("#mobileMenu") ||
          !!a.closest("#mobile-menu") ||
          !!a.closest("#site-header");

        if (inHeader) a.remove();
      }
    });

    // 2) Remove any search form/input that lives inside the header
    const headerRoot = $("header") || $("#site-header") || document;
    const headerSearchForms = $$('form[role="search"], form#site-search', headerRoot);
    headerSearchForms.forEach((f) => f.remove());

    const headerSearchInputs = $$('input[type="search"], input[name="q"], input#q', headerRoot);
    headerSearchInputs.forEach((inp) => {
      const inHeader = !!inp.closest("header") || !!inp.closest("#site-header");
      if (inHeader) {
        const form = inp.closest("form");
        if (form) form.remove();
        else inp.remove();
      }
    });
  }

  // ---------------------------
  // ✅ NEW: Homepage search (submit goes to search.html?q=...)
  // and Search page renders results from existing JSON sources
  // ---------------------------
  async function initSiteSearch() {
    const isHome = page === "index.html" || page === "";
    const isSearchPage = page === "search.html";

    // Helper: get query param
    const params = new URLSearchParams(location.search || "");
    const qParam = safe(params.get("q"));

    // Try to find a search form (supports your "site-search" pattern)
    function findSearchForm() {
      // prefer specific ids if present
      return (
        $("#site-search") ||
        $('form[role="search"]') ||
        null
      );
    }

    function findSearchInput(form) {
      if (!form) return null;
      return (
        $("#q", form) ||
        $('input[type="search"]', form) ||
        $('input[name="q"]', form) ||
        null
      );
    }

    // HOME: bind submit to redirect to search.html
    if (isHome) {
      const form = findSearchForm();
      const input = findSearchInput(form);

      if (form && input) {
        // Don’t double-bind
        if (!form.__tsjBound) {
          form.__tsjBound = true;
          form.addEventListener("submit", (e) => {
            e.preventDefault();
            const q = safe(input.value);
            if (!q) return;
            window.location.href = `search.html?q=${encodeURIComponent(q)}`;
          });
        }
      }
      return;
    }

    // SEARCH PAGE: render results if search.html has a container; otherwise fallback to Google site search
    if (isSearchPage) {
      const query = qParam;

      // If no query, do nothing
      if (!query) return;

      // Try to use your existing IDs (from your snippet pattern)
      const statusEl = $("#search-status");
      const listEl = $("#search-list");
      const wrapEl = $("#search-results") || (listEl ? listEl.closest("section") : null);
      const clearBtn = $("#clear-search");

      // If the page doesn't have containers, fallback to Google site search
      if (!listEl) {
        const google = `https://www.google.com/search?q=${encodeURIComponent("site:topsarkarijobs.com " + query)}`;
        window.location.href = google;
        return;
      }

      // Ensure wrapper visible if it exists
      if (wrapEl) wrapEl.classList.remove("hidden");

      // Clear button behavior if present
      if (clearBtn && !clearBtn.__tsjBound) {
        clearBtn.__tsjBound = true;
        clearBtn.addEventListener("click", () => {
          window.location.href = "search.html";
        });
      }

      function escapeHtml(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
      }

      async function fetchJson(path) {
        const r = await fetch(path, { cache: "no-store" });
        if (!r.ok) throw new Error("Failed: " + path);
        return await r.json();
      }

      // Build a unified searchable pool from existing sources (no new content invented)
      const pool = [];

      // dynamic-sections.json (homepage cards)
      try {
        const ds = await fetchJson("dynamic-sections.json");
        const sections = Array.isArray(ds.sections) ? ds.sections : [];
        sections.forEach((sec) => {
          const items = Array.isArray(sec.items) ? sec.items : [];
          items.forEach((it) => {
            const name = safe(it.name) || safe(it.title);
            const url = safe(it.url || it.link);
            if (!name || !url) return;

            const external = !!it.external;
            pool.push({
              name,
              url: external ? normalizeUrl(url) : openInternal(url, name),
              rawUrl: url,
            });
          });
        });
      } catch (_) {}

      // jobs.json (dropdown & category items)
      try {
        const jobs = await fetchJson("jobs.json");
        const lists = []
          .concat(Array.isArray(jobs.top_jobs) ? jobs.top_jobs : [])
          .concat(Array.isArray(jobs.left_jobs) ? jobs.left_jobs : [])
          .concat(Array.isArray(jobs.right_jobs) ? jobs.right_jobs : []);

        lists.forEach((it) => {
          const name = safe(it.name);
          const url = safe(it.url);
          if (!name || !url) return;

          const external = it.external === true;
          pool.push({
            name,
            url: external ? normalizeUrl(url) : url, // keep EXACT url if it's internal per your jobs.json behavior
            rawUrl: url,
          });
        });
      } catch (_) {}

      // tools.json (tools -> openInternal unless external=true)
      try {
        const tools = await fetchJson("tools.json");
        Object.keys(tools || {}).forEach((k) => {
          const list = Array.isArray(tools[k]) ? tools[k] : [];
          list.forEach((t) => {
            const name = safe(t.name);
            const url = safe(t.url || t.link);
            if (!name || !url) return;

            const external = t.external === true;
            pool.push({
              name,
              url: external ? normalizeUrl(url) : openInternal(url, name),
              rawUrl: url,
            });
          });
        });
      } catch (_) {}

      // Deduplicate by (name|url)
      const seen = new Set();
      const deduped = [];
      pool.forEach((x) => {
        const key = `${x.name}|${x.url}`;
        if (seen.has(key)) return;
        seen.add(key);
        deduped.push(x);
      });

      const q = query.toLowerCase();
      const matches = deduped.filter((x) => (x.name + " " + x.rawUrl).toLowerCase().includes(q));

      if (statusEl) {
        statusEl.textContent = matches.length
          ? `Showing ${matches.length} result(s) for “${query}”.`
          : `No results found for “${query}”. Try SSC, Railway, Bank, Police, Admit Card, Result.`;
      }

      listEl.innerHTML = matches.slice(0, 50).map((r) => {
        return `
          <li class="border border-slate-200 rounded-md p-3 hover:bg-slate-50 transition">
            <a class="font-semibold text-sky-700 underline underline-offset-2" href="${escapeHtml(r.url)}">
              ${escapeHtml(r.name)}
            </a>
            <div class="text-xs text-slate-500 mt-1">${escapeHtml(r.rawUrl)}</div>
          </li>
        `;
      }).join("");

      return;
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
  // Homepage sections (restores homepage content)
  // ---------------------------
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
          ${
            sec.viewMoreUrl
              ? `<a class="view-all" href="${openInternal(sec.viewMoreUrl, title)}">View All <i class="fa-solid fa-arrow-right"></i></a>`
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
      admissions: "Admissions",
      "admit-result": "Admit Card / Result / Answer Key / Syllabus",
      khabar: "Latest Khabar",
      "study-material": "Study Material & Top Courses",
    };

    if (titleEl) titleEl.textContent = groupMeta[group] || "Category";
    if (descEl && groupMeta[group]) {
      if (!safe(descEl.textContent)) descEl.textContent = "";
    }

    async function fetchJson(path) {
      const r = await fetch(path, { cache: "no-store" });
      if (!r.ok) throw new Error("Failed: " + path);
      return await r.json();
    }

    let data;
    try {
      data = await fetchJson("jobs.json");
    } catch (_) {
      gridEl.innerHTML = "";
      if (emptyEl) emptyEl.hidden = false;
      return;
    }

    const top = Array.isArray(data.top_jobs) ? data.top_jobs : [];
    const left = Array.isArray(data.left_jobs) ? data.left_jobs : [];
    const right = Array.isArray(data.right_jobs) ? data.right_jobs : [];

    const isHeader = (x) => x && typeof x === "object" && safe(x.title) && !safe(x.name);
    const isItem = (x) => x && typeof x === "object" && safe(x.name) && safe(x.url);

    function sliceBetween(arr, startIncludes, endIncludes) {
      const startIdx = arr.findIndex(
        (x) => isHeader(x) && safe(x.title).toLowerCase().includes(startIncludes)
      );
      if (startIdx < 0) return [];
      let endIdx = arr.length;
      if (endIncludes) {
        const ei = arr.findIndex(
          (x, i) => i > startIdx && isHeader(x) && safe(x.title).toLowerCase().includes(endIncludes)
        );
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

  // ---------------------------
  // Tools page
  // ---------------------------
  async function initToolsPage() {
    if (page !== "tools.html") return;

    const categoriesView = $("#categories-view");
    const toolsView = $("#tools-view");
    const toolsGrid = $("#tools-grid");
    const toolsTitle = $("#tools-title span") || $("#tools-title");
    const backBtn = $("#back-button");
    const categoryButtons = $$(".category-button");

    if (!categoriesView || !toolsView || !toolsGrid || !categoryButtons.length) return;

    let data = null;
    try {
      const r = await fetch("tools.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const toolsData = (data && typeof data === "object") ? data : {};

    const showCategories = () => {
      toolsView.classList.add("hidden");
      categoriesView.classList.remove("hidden");
      window.scrollTo({ top: 0, behavior: "instant" });
    };

    const showTools = (categoryKey) => {
      const list = Array.isArray(toolsData[categoryKey]) ? toolsData[categoryKey] : [];

      const titleMap = {
        image: "Image Tools",
        pdf: "PDF Tools",
        video: "Video/Audio Tools",
      };
      const titleText = titleMap[categoryKey] || "Tools";
      if (toolsTitle) toolsTitle.textContent = titleText;

      toolsGrid.innerHTML = "";

      if (!list.length) {
        toolsGrid.innerHTML = `
          <div class="col-span-full p-4 bg-white border border-gray-200 rounded-lg text-center text-gray-600">
            No tools found for this category.
          </div>
        `;
      } else {
        list.forEach((t) => {
          const name = safe(t.name) || "Open Tool";
          const url = t.url || t.link || "";
          if (!url) return;

          const isExternal = t.external === true;
          const a = document.createElement("a");
          a.className =
            "p-4 rounded-lg bg-white border border-gray-200 hover:bg-blue-50 hover:border-blue-300 transition duration-300 flex items-start gap-3";
          a.href = isExternal ? normalizeUrl(url) : openInternal(url, name);

          if (isExternal) {
            a.target = "_blank";
            a.rel = "noopener";
          }

          const iconClass = safe(t.icon) || "fas fa-wand-magic-sparkles";
          a.innerHTML = `
            <div class="mt-0.5 text-xl text-blue-600">
              <i class="${iconClass}"></i>
            </div>
            <div>
              <div class="font-semibold text-gray-800">${name}</div>
              <div class="text-sm text-gray-500 mt-1">Open tool</div>
            </div>
          `;
          toolsGrid.appendChild(a);
        });
      }

      categoriesView.classList.add("hidden");
      toolsView.classList.remove("hidden");
      window.scrollTo({ top: 0, behavior: "instant" });
    };

    if (backBtn) backBtn.addEventListener("click", showCategories);

    categoryButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = safe(btn.getAttribute("data-category"));
        if (!key) return;
        showTools(key);
      });
    });

    showCategories();
  }

  // ---------------------------
  // CSC Services (popup + supabase submit)
  // ---------------------------
  const CSC_TABLE = "csc_service_requests";
  let cscSupabase = null;

  async function ensureSupabaseClient() {
    if (cscSupabase) return cscSupabase;

    if (!window.supabase) {
      await new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.src = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2";
        s.async = true;
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
      }).catch(() => null);
    }

    if (!window.supabase) return null;

    try {
      const r = await fetch("config.json", { cache: "no-store" });
      if (!r.ok) return null;
      const config = await r.json();
      if (!config?.supabase?.url || !config?.supabase?.anonKey) return null;

      cscSupabase = window.supabase.createClient(config.supabase.url, config.supabase.anonKey);
      return cscSupabase;
    } catch (_) {
      return null;
    }
  }

  function initCscModal() {
    const modal = $("#cscModal");
    const overlay = $("#cscModalOverlay");
    const closeBtn = $("#cscModalClose");
    const closeBtn2 = $("#cscCloseBtn");
    const form = $("#cscRequestForm");

    if (!modal || !overlay || !closeBtn || !form) return;

    const serviceNameEl = $("#cscServiceName");
    let currentService = { name: "", url: "" };

    const close = () => {
      modal.hidden = true;
      overlay.hidden = true;
      document.body.style.overflow = "";
    };

    const open = (service) => {
      currentService = service || { name: "", url: "" };
      if (serviceNameEl) serviceNameEl.textContent = currentService.name || "Service";

      modal.hidden = false;
      overlay.hidden = false;
      document.body.style.overflow = "hidden";

      const first = $("input, textarea", form);
      if (first) setTimeout(() => first.focus(), 50);
    };

    window.__openCscModal = open;

    overlay.addEventListener("click", close);
    closeBtn.addEventListener("click", close);
    if (closeBtn2) closeBtn2.addEventListener("click", close);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal.hidden) close();
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const fullName = safe($("#cscFullName")?.value);
      const phone = safe($("#cscPhone")?.value);
      const state = safe($("#cscState")?.value);
      const msg = safe($("#cscMessage")?.value);

      if (!fullName || !phone || phone.length < 8) {
        alert("Please fill all fields correctly.");
        return;
      }

      const sb = await ensureSupabaseClient();
      if (!sb) {
        alert("Submission system is temporarily unavailable. Please try again later.");
        return;
      }

      const serviceText = [
        safe(currentService.name) ? safe(currentService.name) : "-",
        state ? `State: ${state}` : "",
        currentService.url ? `Link: ${normalizeUrl(currentService.url)}` : "",
        msg ? `Details: ${msg}` : "",
      ]
        .filter(Boolean)
        .join("\n");

      try {
        const { error } = await sb.from(CSC_TABLE).insert([
          {
            name: fullName,
            phone: phone,
            service: serviceText,
            created_at: new Date().toISOString(),
          },
        ]);

        if (error) {
          console.error("Supabase insert error:", error);
          alert("Failed to submit your request. Please try again.");
          return;
        }

        alert("Request submitted successfully. We will contact you soon.");
        form.reset();
        close();
      } catch (err) {
        console.error("Submit error:", err);
        alert("Could not submit your request. Please check your connection and try again.");
      }
    });
  }

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
      const url = s.url || s.link || "";
      if (!name) return;

      const a = document.createElement("a");
      a.className = "section-link csc-service-link";
      a.href = "#";
      a.setAttribute("role", "button");
      a.innerHTML = `
        <div class="t">${name}</div>
        <div class="d">Click to fill details & submit request</div>
      `;

      a.addEventListener("click", (e) => {
        e.preventDefault();
        if (typeof window.__openCscModal === "function") {
          window.__openCscModal({ name, url });
        }
      });

      list.appendChild(a);
    });
  }

  // ---------------------------
  // Boot
  // ---------------------------
  document.addEventListener("DOMContentLoaded", async () => {
    await injectHeaderFooter();

    await loadHeaderLinks();

    // ✅ MUST run after header injection
    removeHeaderSearchEverywhereExceptHome();

    initOffcanvas();
    initDropdowns();
    initFAQ();

    // ✅ Homepage & search page behavior
    await initSiteSearch();

    if (page === "index.html" || page === "") {
      await renderHomepageSections();
    }

    await initCategoryPage();
    await initToolsPage();

    if (page === "govt-services.html") {
      ensureSupabaseClient().catch(() => {});
    }
    initCscModal();
    await renderServicesPage();
  });
})();
