(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  // -------------------------
  // Header links (CTA buttons)
  // -------------------------
  async function loadHeaderLinks() {
    let headerData = { header_links: [], home_links: [], social_links: [] };
    try {
      const r = await fetch("header_links.json", { cache: "no-store" });
      if (r.ok) headerData = await r.json();
    } catch (_) {}

    const desktop = $("#header-links");
    const mobile = $("#header-links-mobile");
    const footerSocial = $("#footer-social-links");

    // CTA buttons
    const links = headerData.header_links || [];
    if (desktop) {
      desktop.innerHTML = "";
      links.forEach((l) => {
        const a = document.createElement("a");
        a.href = l.link || l.url || "#";
        a.target = "_blank";
        a.rel = "noopener";
        a.className = "nav-link";
        a.textContent = l.name || "Link";
        desktop.appendChild(a);
      });
    }

    if (mobile) {
      mobile.innerHTML = "";
      links.forEach((l) => {
        const a = document.createElement("a");
        a.href = l.link || l.url || "#";
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = l.name || "Link";
        mobile.appendChild(a);
      });
    }

    // Footer social
    const socials = headerData.social_links || [];
    if (footerSocial) {
      footerSocial.innerHTML = "";
      socials.forEach((s) => {
        const a = document.createElement("a");
        a.href = s.url || "#";
        a.target = "_blank";
        a.rel = "noopener";
        a.className = "nav-link";
        a.textContent = s.name || "Social";
        footerSocial.appendChild(a);
      });
    }

    return headerData;
  }

  // -------------------------
  // Mobile offcanvas menu
  // -------------------------
  function initOffcanvas() {
    const menuBtn = $("#menuBtn");
    const closeBtn = $("#closeMenuBtn");
    const menu = $("#mobileMenu");
    const overlay = $("#menuOverlay");

    if (!menuBtn || !closeBtn || !menu || !overlay) return;

    const open = () => {
      menu.hidden = false;
      overlay.hidden = false;
      menuBtn.setAttribute("aria-expanded", "true");
      // focus first link
      const first = $("a", menu);
      if (first) first.focus();
      document.body.style.overflow = "hidden";
    };

    const close = () => {
      menu.hidden = true;
      overlay.hidden = true;
      menuBtn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
      menuBtn.focus();
    };

    menuBtn.addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    overlay.addEventListener("click", close);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !menu.hidden) close();
    });

    // close on link click
    $$("a", menu).forEach((a) => a.addEventListener("click", close));
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

      // keyboard
      btn.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          const first = $(".nav-dd-item", menu);
          if (first) first.focus();
        }
      });

      $$("a", menu).forEach((a) => {
        a.addEventListener("keydown", (e) => {
          if (e.key === "Escape") {
            closeAll();
            btn.focus();
          }
        });
      });
    });

    document.addEventListener("click", (e) => {
      const inside = e.target.closest("[data-dd]");
      if (!inside) closeAll();
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
        // close all
        $$(".faq-btn").forEach((b) => {
          b.setAttribute("aria-expanded", "false");
          const panel = b.parentElement.querySelector(".faq-panel");
          if (panel) panel.hidden = true;
        });
        // open current if was closed
        if (!expanded) {
          btn.setAttribute("aria-expanded", "true");
          const panel = btn.parentElement.querySelector(".faq-panel");
          if (panel) panel.hidden = false;
        }
      });
    });
  }

  // -------------------------
  // Helpers
  // -------------------------
  function safeText(v) {
    return (v || "").toString().trim();
  }

  function highlight(text, q) {
    const t = safeText(text);
    const query = safeText(q);
    if (!query) return t;
    const re = new RegExp(`(${escapeRegExp(query)})`, "ig");
    return t.replace(re, "<mark>$1</mark>");
  }

  function escapeRegExp(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function normalizeGroupParam(g) {
    const v = (g || "").toLowerCase().trim();
    // allow multiple aliases
    const map = {
      "study": "study",
      "study-wise": "study",
      "studywise": "study",

      "popular": "popular",
      "popular-jobs": "popular",

      "state": "state",
      "state-wise": "state",
      "statewise": "state",

      "admissions": "admissions",
      "admission": "admissions",

      "admit-result": "admit-result",
      "result-admit": "admit-result",

      "khabar": "khabar",
      "news": "khabar",

      "study-material": "study-material",
      "courses": "study-material",

      "tools": "tools"
    };
    return map[v] || v || "study";
  }

  function groupMeta(group) {
    const meta = {
      "study": {
        title: "Study wise Jobs",
        desc: "Browse government job links by education level — 8th, 10th, 12th, ITI, diploma, graduation and more."
      },
      "popular": {
        title: "Popular Job Categories",
        desc: "Browse popular government job categories like SSC, Railway, Bank, Police, Teaching and more."
      },
      "state": {
        title: "State wise Jobs",
        desc: "Find state-wise government job links and recruitment updates."
      },
      "admissions": {
        title: "Admissions",
        desc: "Admissions updates and official application links."
      },
      "admit-result": {
        title: "Admit Card / Result / Answer Key / Syllabus",
        desc: "Quick access to admit cards, results, answer keys and syllabus links."
      },
      "khabar": {
        title: "Latest Khabar",
        desc: "Latest news, updates and useful information related to jobs and exams."
      },
      "study-material": {
        title: "Study Material & Top Courses",
        desc: "Study resources, notes and recommended courses."
      },
      "tools": {
        title: "Tools",
        desc: "Quick tools to help with forms, PDFs and utilities."
      }
    };
    return meta[group] || { title: "Category", desc: "Browse links and categories." };
  }

  // -------------------------
  // Homepage: big sections
  // -------------------------
  async function loadHomepageDynamicSections() {
    const wrap = $("#dynamic-sections");
    if (!wrap) return;

    let data = { sections: [] };
    try {
      const r = await fetch("dynamic-sections.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    wrap.innerHTML = "";

    const sections = Array.isArray(data.sections) ? data.sections : [];
    sections.forEach((sec) => {
      const title = safeText(sec.title) || "Updates";
      const color = safeText(sec.color) || "#0284c7";
      const icon = safeText(sec.icon) || "fa-solid fa-briefcase";

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
          <a class="view-all" href="view.html?section=${encodeURIComponent(safeText(sec.id)||'')}">
            View All <i class="fa-solid fa-arrow-right"></i>
          </a>
        </div>
      `;

      const list = $(".section-list", card);
      const items = Array.isArray(sec.items) ? sec.items.slice(0, 8) : [];
      items.forEach((it) => {
        const name = safeText(it.name) || "Open";
        const date = safeText(it.date);
        const url = it.url || it.link || "";
        const external = !!it.external;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = external ? url : `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`;
        if (external) {
          a.target = "_blank";
          a.rel = "noopener";
        }
        a.innerHTML = `
          <div class="t">${name}</div>
          ${date ? `<div class="d">${date}</div>` : ``}
        `;
        list.appendChild(a);
      });

      wrap.appendChild(card);
    });
  }

  // -------------------------
  // Category page: extract blocks from jobs.json
  // -------------------------
  async function loadCategoryPage() {
    if (page !== "category.html") return;

    const params = new URLSearchParams(location.search);
    const group = normalizeGroupParam(params.get("group"));

    const meta = groupMeta(group);
    $("#categoryTitle").textContent = meta.title;
    $("#crumbText").textContent = meta.title;
    $("#categoryDesc").textContent = meta.desc;
    document.title = `${meta.title} | Top Sarkari Jobs`;

    const grid = $("#categoryGrid");
    const empty = $("#categoryEmpty");
    const filter = $("#categoryFilter");
    const clearBtn = $("#clearCategoryFilter");

    let jobs = null;
    try {
      const r = await fetch("jobs.json", { cache: "no-store" });
      if (r.ok) jobs = await r.json();
    } catch (_) {}

    // If jobs.json not available, show empty
    if (!jobs) {
      grid.innerHTML = "";
      empty.style.display = "block";
      return;
    }

    // Where are your category links stored?
    // Many repos store them inside: top_jobs / left_jobs / right_jobs arrays with title separators.
    const pool = []
      .concat(Array.isArray(jobs.top_jobs) ? jobs.top_jobs : [])
      .concat(Array.isArray(jobs.left_jobs) ? jobs.left_jobs : [])
      .concat(Array.isArray(jobs.right_jobs) ? jobs.right_jobs : []);

    // Map group -> which "title" headings to match
    // (These should match your jobs.json titles. Add more synonyms here if needed.)
    const titleMatchers = {
      "study": [/study/i],
      "popular": [/popular/i],
      "state": [/state/i],
      "admissions": [/admission/i],
      "admit-result": [/admit/i, /result/i, /answer/i, /syllabus/i],
      "khabar": [/khabar/i, /news/i],
      "study-material": [/study material/i, /course/i, /books?/i],
      "tools": [/tools?/i]
    };

    const matchers = titleMatchers[group] || [/.*/];

    // Extract blocks:
    // When an item has {title:true} or item.title (string), treat as heading.
    // Collect all items under matching headings until next heading.
    const blocks = [];
    let currentHeading = null;
    let currentItems = [];

    function flush() {
      if (currentHeading && currentItems.length) {
        blocks.push({ heading: currentHeading, items: currentItems });
      }
      currentHeading = null;
      currentItems = [];
    }

    for (const item of pool) {
      const isHeading = !!item.title && typeof item.title === "string";

      if (isHeading) {
        // heading change
        flush();
        const h = safeText(item.title);
        const isMatch = matchers.some((re) => re.test(h));
        currentHeading = isMatch ? h : null;
        currentItems = [];
        continue;
      }

      // normal link item
      if (!currentHeading) continue;

      const name = safeText(item.name);
      const url = item.url || item.link || "";
      if (!name || !url) continue;

      currentItems.push({
        name,
        url,
        external: !!item.external
      });
    }
    flush();

    // Render blocks
    renderCategoryBlocks(blocks);

    // Filter on category page
    if (filter) {
      filter.addEventListener("input", () => {
        const q = safeText(filter.value).toLowerCase();
        if (!q) {
          renderCategoryBlocks(blocks);
          return;
        }
        const filtered = blocks
          .map((b) => ({
            heading: b.heading,
            items: b.items.filter((x) => x.name.toLowerCase().includes(q))
          }))
          .filter((b) => b.items.length);

        renderCategoryBlocks(filtered, q);
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        if (!filter) return;
        filter.value = "";
        renderCategoryBlocks(blocks);
        filter.focus();
      });
    }

    function renderCategoryBlocks(blocksToRender, q = "") {
      grid.innerHTML = "";
      if (!blocksToRender.length) {
        empty.style.display = "block";
        return;
      }
      empty.style.display = "none";

      blocksToRender.forEach((b) => {
        const card = document.createElement("article");
        card.className = "section-card";

        // stable color based on group
        const colorMap = {
          "study": "#2563eb",
          "popular": "#db2777",
          "state": "#059669",
          "admissions": "#f59e0b",
          "admit-result": "#ef4444",
          "khabar": "#7c3aed",
          "study-material": "#0ea5e9",
          "tools": "#0f172a"
        };

        const color = colorMap[group] || "#0284c7";

        card.innerHTML = `
          <div class="section-head" style="background:${color}">
            <div class="left">
              <i class="fa-solid fa-layer-group"></i>
              <span>${b.heading}</span>
            </div>
          </div>
          <div class="section-body">
            <div class="section-list"></div>
          </div>
        `;

        const list = $(".section-list", card);
        b.items.forEach((it) => {
          const a = document.createElement("a");
          a.className = "section-link";
          const href = it.external
            ? it.url
            : `view.html?url=${encodeURIComponent(it.url)}&name=${encodeURIComponent(it.name)}`;

          a.href = href;
          if (it.external) {
            a.target = "_blank";
            a.rel = "noopener";
          }
          a.innerHTML = `
            <div class="t">${q ? highlight(it.name, q) : it.name}</div>
            <div class="d">Open official link</div>
          `;
          list.appendChild(a);
        });

        grid.appendChild(card);
      });
    }
  }

  // -------------------------
  // Site-wide search index
  // -------------------------
  let SEARCH_INDEX = [];
  let SEARCH_READY = false;

  async function buildSearchIndex() {
    if (SEARCH_READY) return;

    const entries = [];

    // dynamic sections
    try {
      const r = await fetch("dynamic-sections.json", { cache: "no-store" });
      if (r.ok) {
        const ds = await r.json();
        (ds.sections || []).forEach((s) => {
          (s.items || []).forEach((it) => {
            const name = safeText(it.name);
            const url = it.url || it.link || "";
            if (!name || !url) return;
            entries.push({
              title: name,
              meta: safeText(s.title) || "Updates",
              href: it.external ? url : `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`,
              external: !!it.external
            });
          });
        });
      }
    } catch (_) {}

    // jobs categories
    try {
      const r = await fetch("jobs.json", { cache: "no-store" });
      if (r.ok) {
        const jobs = await r.json();
        const pool = []
          .concat(jobs.top_jobs || [])
          .concat(jobs.left_jobs || [])
          .concat(jobs.right_jobs || []);
        pool.forEach((it) => {
          if (it && it.title) return;
          const name = safeText(it.name);
          const url = it.url || it.link || "";
          if (!name || !url) return;
          entries.push({
            title: name,
            meta: "Jobs / Categories",
            href: it.external ? url : `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`,
            external: !!it.external
          });
        });
      }
    } catch (_) {}

    // tools + services (optional)
    try {
      const r = await fetch("tools.json", { cache: "no-store" });
      if (r.ok) {
        const t = await r.json();
        ["image","pdf","video"].forEach((k) => {
          (t[k] || []).forEach((it) => {
            const name = safeText(it.name);
            const url = it.url || "";
            if (!name || !url) return;
            entries.push({
              title: name,
              meta: "Tools",
              href: it.external ? url : `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}&type=tool`,
              external: !!it.external
            });
          });
        });
      }
    } catch (_) {}

    try {
      const r = await fetch("services.json", { cache: "no-store" });
      if (r.ok) {
        const s = await r.json();
        (s.services || s || []).forEach((it) => {
          const name = safeText(it.name || it.service);
          if (!name) return;
          entries.push({
            title: name,
            meta: "CSC Services",
            href: "govt-services.html",
            external: false
          });
        });
      }
    } catch (_) {}

    // de-dup
    const seen = new Set();
    SEARCH_INDEX = entries.filter((e) => {
      const key = (e.title + "|" + e.href).toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    SEARCH_READY = true;
  }

  function initSearchUI() {
    const input = $("#siteSearchInput");
    const btn = $("#siteSearchBtn");
    const results = $("#searchResults");
    const openSearchBtn = $("#openSearchBtn");

    if (!input || !btn || !results) return;

    const run = async () => {
      const q = safeText(input.value);
      if (!q) {
        results.classList.remove("open");
        results.innerHTML = "";
        return;
      }

      await buildSearchIndex();

      const ql = q.toLowerCase();
      const matches = SEARCH_INDEX
        .filter((e) => e.title.toLowerCase().includes(ql) || e.meta.toLowerCase().includes(ql))
        .slice(0, 25);

      if (!matches.length) {
        results.classList.add("open");
        results.innerHTML = `<div class="result-item"><div><div class="result-title">No results found</div><div class="result-meta">Try a different keyword.</div></div></div>`;
        return;
      }

      results.classList.add("open");
      results.innerHTML = matches.map((m) => {
        return `
          <a class="result-item" href="${m.href}" ${m.external ? `target="_blank" rel="noopener"` : ""}>
            <div>
              <div class="result-title">${highlight(m.title, q)}</div>
              <div class="result-meta">${m.meta}</div>
            </div>
            <div class="result-meta">${m.external ? "↗" : "→"}</div>
          </a>
        `;
      }).join("");
    };

    // desktop/mobile open search button just focuses input
    if (openSearchBtn) {
      openSearchBtn.addEventListener("click", () => {
        input.scrollIntoView({ behavior: "smooth", block: "center" });
        setTimeout(() => input.focus(), 200);
      });
    }

    btn.addEventListener("click", run);
    input.addEventListener("input", debounce(run, 140));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") run();
      if (e.key === "Escape") {
        results.classList.remove("open");
        results.innerHTML = "";
        input.blur();
      }
    });

    document.addEventListener("click", (e) => {
      const inside = e.target.closest(".search-card");
      if (!inside) {
        results.classList.remove("open");
      }
    });

    // auto-run if ?q=
    const params = new URLSearchParams(location.search);
    const q = params.get("q");
    if (q) {
      input.value = q;
      run();
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
    initSearchUI();

    if (page === "index.html" || page === "") {
      await loadHomepageDynamicSections();
    }

    await loadCategoryPage();
  });

})();
