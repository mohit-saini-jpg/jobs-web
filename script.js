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

  function openInternal(url, name) {
    const u = normalizeUrl(url);
    return `view.html?url=${encodeURIComponent(u)}&name=${encodeURIComponent(name)}`;
  }

  window.goBack = () => {
    if (window.history.length > 1) window.history.back();
    else window.location.href = "index.html";
  };

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

  // --------------------------------------------------------------------
  // ✅ SAFE PATCH:
  // 1) Hide ALL search UI on NON-home pages (header search + big search box).
  // 2) Homepage search works: redirects to Google site search across your site.
  //    - If there’s an input: use it.
  //    - If only a button exists: prompt for query.
  // --------------------------------------------------------------------
  function enforceSearchVisibilityAndHomeSearch() {
    const isHome = page === "index.html" || page === "";

    // Hide helper (NEVER removes nodes)
    const hide = (el) => {
      if (!el) return;
      if (el.dataset && el.dataset.searchHidden === "1") return;
      el.style.setProperty("display", "none", "important");
      if (el.dataset) el.dataset.searchHidden = "1";
    };

    // Find header root (injected)
    const headerRoot = document.getElementById("site-header") || document.querySelector("header") || null;

    // --- A) Hide header search UI on NON-home pages ---
    if (!isHome && headerRoot) {
      // Hide anything in header that looks like search UI
      const headerSearchSelectors = [
        'form[role="search"]',
        'form#site-search',
        'input[type="search"]',
        'input[name="q"]',
        'input#q',
        'input#search',
        'input#searchInput',
        '[class*="search" i]',
        '[id*="search" i]',
        'button[aria-label*="search" i]',
        'button[title*="search" i]',
        'a[href*="search" i]',
      ];

      headerSearchSelectors.forEach((sel) => {
        headerRoot.querySelectorAll(sel).forEach((node) => {
          // Only hide elements that are truly inside the header/nav area
          const inHeader = node.closest("#site-header") || node.closest("header") || node.closest("nav");
          if (!inHeader) return;

          // Do NOT hide the whole header container by accident
          if (node.id === "site-header") return;
          if (node.tagName === "HEADER") return;
          if (node.tagName === "NAV" && (node.children?.length || 0) > 2) return;

          // Hide the closest sensible wrapper
          const wrapper =
            node.closest(".search-container") ||
            node.closest(".nav-search") ||
            node.closest("form") ||
            node;

          hide(wrapper);
        });
      });

      // Also hide any link/button whose visible text is "Search" in header
      headerRoot.querySelectorAll("a,button").forEach((el) => {
        const t = safe(el.textContent).toLowerCase();
        if (t === "search" || t.includes("search")) {
          const inHeader = el.closest("#site-header") || el.closest("header") || el.closest("nav");
          if (inHeader) hide(el);
        }
      });
    }

    // --- B) Hide the BIG homepage search section on NON-home pages ---
    // This is the box in your screenshot: "Search across Top Sarkari Jobs"
    if (!isHome) {
      const needles = [
        "search across top sarkari jobs",
        "search jobs, results, admit cards", // subtitle text
      ];

      // Look for headings/paragraphs that contain the exact text and hide their container.
      const candidates = $$("h1,h2,h3,h4,p,div,section");
      candidates.forEach((node) => {
        const text = safe(node.textContent).toLowerCase();
        if (!text) return;

        const hit = needles.some((n) => text.includes(n));
        if (!hit) return;

        // Hide the nearest “card/section” wrapper, not the whole page
        const box =
          node.closest("section") ||
          node.closest(".container") ||
          node.closest(".max-w-6xl") ||
          node.closest(".max-w-5xl") ||
          node.closest(".max-w-4xl") ||
          node.closest(".rounded") ||
          node.closest(".shadow") ||
          node.parentElement;

        // Safety: never hide main/page wrappers
        if (!box) return;
        if (box.tagName === "BODY") return;
        if (box.id === "site-header") return;
        if (box.id === "site-footer") return;

        hide(box);
      });
    }

    // --- C) Make HOMEPAGE search work site-wide ---
    if (isHome) {
      const go = (q) => {
        const query = safe(q);
        if (!query) return;
        // Works across the entire website with no backend needed
        const url =
          "https://www.google.com/search?q=" +
          encodeURIComponent("site:topsarkarijobs.com " + query);
        window.location.href = url;
      };

      // Prefer input in header, else any search input on page
      const input =
        (headerRoot && (headerRoot.querySelector('input[type="search"]') ||
                        headerRoot.querySelector('input[name="q"]') ||
                        headerRoot.querySelector("#q") ||
                        headerRoot.querySelector("#searchInput"))) ||
        document.querySelector('input[type="search"]') ||
        document.querySelector('input[name="q"]') ||
        document.querySelector("#q") ||
        document.querySelector("#searchInput") ||
        null;

      const form = input ? input.closest("form") : null;

      // Bind submit/enter for input-based search
      if (input) {
        if (!input.dataset.boundHomeSearchEnter) {
          input.dataset.boundHomeSearchEnter = "1";
          input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              go(input.value);
            }
          });
        }

        if (form && !form.dataset.boundHomeSearchSubmit) {
          form.dataset.boundHomeSearchSubmit = "1";
          form.addEventListener("submit", (e) => {
            e.preventDefault();
            go(input.value);
          });
        }
      }

      // If homepage search UI is button-only (no input), bind button to prompt
      const btns = $$("button,a");
      btns.forEach((b) => {
        const t = safe(b.textContent).toLowerCase();
        if (!t) return;
        if (t !== "search" && !t.includes("search")) return;

        // Only bind obvious homepage search buttons (avoid nav buttons)
        const looksLikeHeroSearch =
          !!b.closest("main") && !b.closest("nav") && !b.closest("header");

        if (!looksLikeHeroSearch) return;

        if (b.dataset.boundHomeSearchBtn === "1") return;
        b.dataset.boundHomeSearchBtn = "1";

        b.addEventListener("click", (e) => {
          // If there is an input, let it handle
          if (input) return;
          e.preventDefault();
          const q = prompt("Search Top Sarkari Jobs:");
          if (q) go(q);
        });
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
      a.href = url; // EXACT URL FROM jobs.json
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

    const toolsData = data && typeof data === "object" ? data : {};

    const showCategories = () => {
      toolsView.classList.add("hidden");
      categoriesView.classList.remove("hidden");
      window.scrollTo({ top: 0, behavior: "instant" });
    };

    const showTools = (categoryKey) => {
      const list = Array.isArray(toolsData[categoryKey]) ? toolsData[categoryKey] : [];

      const titleMap = { image: "Image Tools", pdf: "PDF Tools", video: "Video/Audio Tools" };
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

  // Boot
  document.addEventListener("DOMContentLoaded", async () => {
    await injectHeaderFooter();
    await loadHeaderLinks();

    // ✅ SAFE search behavior & hiding (won’t touch header itself)
    enforceSearchVisibilityAndHomeSearch();

    initOffcanvas();
    initDropdowns();
    initFAQ();

    if (page === "index.html" || page === "") {
      await renderHomepageSections();
    }

    await initCategoryPage();
    await initToolsPage();
  });
})();
