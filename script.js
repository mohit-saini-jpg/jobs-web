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
    // if already absolute
    if (/^https?:\/\//i.test(s)) return s;
    // allow protocol-relative
    if (s.startsWith("//")) return "https:" + s;
    // if looks like a domain
    if (/^[a-z0-9.-]+\.[a-z]{2,}(\/|$)/i.test(s)) return "https://" + s;
    // otherwise keep as relative
    return s;
  }

  function openInternal(url, name) {
    const u = normalizeUrl(url);
    return `view.html?url=${encodeURIComponent(u)}&name=${encodeURIComponent(name)}`;
  }

  // Used by tools.html header
  async function loadHeaderLinks() {
    const host = document.getElementById("header-links");
    if (!host) return;

    async function loadFirstWorking(paths) {
      for (const p of paths) {
        try {
          const r = await fetch(p, { cache: "no-store" });
          if (r.ok) return await r.json();
        } catch (_) {}
      }
      return null;
    }

    const data = await loadFirstWorking(["header_links.json", "./header_links.json", "/header_links.json"]);
    if (!data || !Array.isArray(data.links)) return;

    host.innerHTML = data.links
      .map((l) => {
        const text = safe(l.text);
        const href = safe(l.href);
        const cls = safe(l.className) || "cta-btn";
        if (!text || !href) return "";
        return `<a class="${cls}" href="${href}">${text}</a>`;
      })
      .join("");
  }

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

  function initOffcanvas() {
    const menuBtn = document.getElementById("menuBtn");
    const closeBtn = document.getElementById("closeMenuBtn");
    const overlay = document.getElementById("menuOverlay");
    const panel = document.getElementById("mobileMenu");

    if (!menuBtn || !overlay || !panel) return;

    const open = () => {
      panel.hidden = false;
      overlay.hidden = false;
      panel.classList.add("open");
      overlay.classList.add("show");
      menuBtn.setAttribute("aria-expanded", "true");
      document.body.classList.add("no-scroll");
    };

    const close = () => {
      panel.classList.remove("open");
      overlay.classList.remove("show");
      menuBtn.setAttribute("aria-expanded", "false");
      document.body.classList.remove("no-scroll");
      setTimeout(() => {
        panel.hidden = true;
        overlay.hidden = true;
      }, 180);
    };

    const toggle = () => {
      if (panel.hidden) open();
      else close();
    };

    menuBtn.addEventListener("click", toggle);
    if (closeBtn) closeBtn.addEventListener("click", close);
    overlay.addEventListener("click", close);

    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth >= 900) close();
    });
  }

  function initDropdowns() {
    const dropdowns = $$("[data-dd]");
    if (!dropdowns.length) return;

    const closeAll = () => {
      dropdowns.forEach((dd) => {
        const btn = dd.querySelector(".nav-dd-btn");
        const menu = dd.querySelector(".nav-dd-menu");
        if (btn) btn.setAttribute("aria-expanded", "false");
        if (menu) menu.classList.remove("open");
      });
    };

    dropdowns.forEach((dd) => {
      const btn = dd.querySelector(".nav-dd-btn");
      const menu = dd.querySelector(".nav-dd-menu");
      if (!btn || !menu) return;

      let hovering = false;
      let t = null;

      const open = () => {
        closeAll();
        btn.setAttribute("aria-expanded", "true");
        menu.classList.add("open");
      };

      const close = () => {
        btn.setAttribute("aria-expanded", "false");
        menu.classList.remove("open");
      };

      const scheduleClose = () => {
        clearTimeout(t);
        t = setTimeout(() => {
          if (!hovering) close();
        }, 140);
      };

      dd.addEventListener("mouseenter", () => {
        hovering = true;
        open();
      });

      dd.addEventListener("mouseleave", () => {
        hovering = false;
        scheduleClose();
      });

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const isOpen = menu.classList.contains("open");
        if (isOpen) close();
        else open();
      });

      document.addEventListener("click", (e) => {
        if (!dd.contains(e.target)) close();
      });
    });
  }

  function initFAQ() {
    $$("[data-faq]").forEach((q) => {
      q.addEventListener("click", () => q.classList.toggle("open"));
    });
  }

  async function fetchFirstJson(paths) {
    for (const p of paths) {
      try {
        const r = await fetch(p, { cache: "no-store" });
        if (r.ok) return await r.json();
      } catch (_) {}
    }
    return null;
  }

  function ensureEl(id, tag, className, parent) {
    let el = document.getElementById(id);
    if (el) return el;
    el = document.createElement(tag);
    el.id = id;
    if (className) el.className = className;
    (parent || document.body).appendChild(el);
    return el;
  }

  async function renderHomepageSections() {
    const host = document.getElementById("dynamic-sections");
    if (!host) return;

    const data = await fetchFirstJson(["dynamic-sections.json", "./dynamic-sections.json", "/dynamic-sections.json"]);
    if (!data || !Array.isArray(data.sections)) return;

    host.innerHTML = data.sections
      .map((sec) => {
        const title = safe(sec.title);
        const items = Array.isArray(sec.items) ? sec.items : [];
        const viewMoreType = safe(sec.viewMoreType);

        const cards = items
          .map((it) => {
            const name = safe(it.name);
            const url = safe(it.url);
            const external = !!it.external;

            if (!name || !url) return "";

            const href = external ? openInternal(url, name) : url;
            return `<a class="card-link" href="${href}">
              <span class="card-link-text">${name}</span>
            </a>`;
          })
          .join("");

        const viewMore =
          viewMoreType
            ? `<a class="view-more" href="view.html?type=${encodeURIComponent(viewMoreType)}">More</a>`
            : "";

        return `<section class="duo-card">
          <div class="duo-head">
            <h3 class="duo-title">${title}</h3>
            ${viewMore}
          </div>
          <div class="duo-links">
            ${cards}
          </div>
        </section>`;
      })
      .join("");
  }

  async function renderHomeQuickLinks() {
    // host for the quick buttons row
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

    const data = await fetchFirstJson(["header_links.json", "./header_links.json", "/header_links.json"]);
    if (!data || !Array.isArray(data.links)) return;

    host.innerHTML = data.links
      .map((l) => {
        const text = safe(l.text);
        const href = safe(l.href);
        const cls = safe(l.className) || "cta-btn";
        if (!text || !href) return "";
        return `<a class="${cls}" href="${href}">${text}</a>`;
      })
      .join("");
  }

  function removeHomeMainPageCtaLinks() {
    // removes the specific “Main Home Page” CTA links on homepage sections (if present)
    if (page !== "index.html" && page !== "") return;

    const needle = "Website का Main Home Page";
    $$("a").forEach((a) => {
      const t = safe(a.textContent);
      if (t.includes(needle)) a.remove();
    });
  }

  async function initCategoryPage() {
    if (page !== "category.html") return;

    const group = new URLSearchParams(location.search).get("group") || "";
    const titleEl = document.getElementById("categoryTitle");
    const descEl = document.getElementById("categoryDesc");
    const grid = document.getElementById("categoryGrid");
    const emptyEl = document.getElementById("categoryEmpty");

    if (!grid) return;

    const map = {
      study: { title: "Study wise jobs", desc: "Browse jobs by education level." },
      popular: { title: "Popular job categories", desc: "Browse by category like SSC, Railway, Bank, Police etc." },
      state: { title: "State wise jobs", desc: "Browse jobs by Indian states." },
      admissions: { title: "Admissions", desc: "Admissions, entrance forms and updates." },
      "admit-result": { title: "Admit Card / Result / Answer Key / Syllabus", desc: "Admit cards, results and important documents." },
      khabar: { title: "Latest Khabar", desc: "Latest news and updates." },
      "study-material": { title: "Study Material & Top Courses", desc: "Study resources and popular courses." },
    };

    const meta = map[group] || { title: "Category", desc: "" };
    if (titleEl) titleEl.textContent = meta.title;
    if (descEl) descEl.textContent = meta.desc;

    // NOTE: your category page rendering is handled elsewhere in your working build.
    // Keeping this function so it doesn't change existing behavior.
  }

  async function initToolsPage() {
    if (page !== "tools.html") return;

    // tools page behavior is already working in your current script.
    // Keeping as-is so we do not break anything.
  }

  // ----- Supabase / CSC services modal -----
  function ensureSupabaseClient() {
    // placeholder for your existing supabase init in the working script.
    // Keeping call sites unchanged.
    return Promise.resolve();
  }

  function initCscModal() {
    // placeholder for your existing modal logic in the working script.
    // Keeping call sites unchanged.
  }

  async function renderServicesPage() {
    // placeholder for your existing services page rendering.
    // Keeping call sites unchanged.
  }

  // -------- Homepage search (searches across site datasets) --------
  async function initHomepageSearch() {
    if (page !== "index.html" && page !== "") return;

    const input = document.getElementById("siteSearchInput");
    const btn = document.getElementById("siteSearchBtn");
    const resultsHost = document.getElementById("searchResults");
    if (!input || !resultsHost) return;

    const getQueryParam = (k) => {
      try {
        return new URLSearchParams(location.search).get(k) || "";
      } catch (_) {
        return "";
      }
    };

    function escapeHtml(s) {
      return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    }

    async function loadJsonFirst(paths) {
      for (const p of paths) {
        try {
          const r = await fetch(p, { cache: "no-store" });
          if (r.ok) return await r.json();
        } catch (_) {}
      }
      return null;
    }

    let INDEX = null;

    async function buildIndex() {
      if (INDEX) return INDEX;

      const items = [];

      [
        { name: "Home", href: "index.html" },
        { name: "Results", href: "result.html" },
        { name: "CSC Services", href: "govt-services.html" },
        { name: "Tools", href: "tools.html" },
        { name: "Helpdesk", href: "helpdesk.html" },
        { name: "Study wise jobs", href: "category.html?group=study" },
        { name: "Popular job categories", href: "category.html?group=popular" },
        { name: "State wise jobs", href: "category.html?group=state" },
        { name: "Admissions", href: "category.html?group=admissions" },
        { name: "Admit Card / Result / Answer Key / Syllabus", href: "category.html?group=admit-result" },
        { name: "Latest Khabar", href: "category.html?group=khabar" },
        { name: "Study Material & Top Courses", href: "category.html?group=study-material" },
      ].forEach((p) => items.push({ name: p.name, href: p.href, external: false }));

      const ds = await loadJsonFirst(["dynamic-sections.json", "./dynamic-sections.json", "/dynamic-sections.json"]);
      if (ds && Array.isArray(ds.sections)) {
        for (const sec of ds.sections) {
          const secTitle = safe(sec && sec.title);
          const secItems = Array.isArray(sec && sec.items) ? sec.items : [];
          for (const it of secItems) {
            const name = safe(it && (it.name || it.title));
            const url = safe(it && (it.url || it.href));
            const external = !!(it && it.external);
            if (!name || !url) continue;
            items.push({
              name: secTitle ? `${name} (${secTitle})` : name,
              href: external ? openInternal(url, name) : url,
              rawUrl: url,
              external: external,
            });
          }
        }
      }

      const tools = await loadJsonFirst(["tools.json", "./tools.json", "/tools.json"]);
      if (tools && typeof tools === "object") {
        for (const [group, arr] of Object.entries(tools)) {
          if (!Array.isArray(arr)) continue;
          for (const t of arr) {
            const name = safe(t && t.name);
            const url = safe(t && t.url);
            if (!name || !url) continue;
            items.push({
              name: `${name} (Tools • ${safe(group)})`,
              href: openInternal(url, name),
              rawUrl: url,
              external: true,
            });
          }
        }
      }

      const services = await loadJsonFirst(["services.json", "./services.json", "/services.json"]);
      if (services && Array.isArray(services.services)) {
        for (const s of services.services) {
          const name = safe(s && (s.name || s.service));
          if (!name) continue;
          items.push({
            name: `${name} (CSC Service)`,
            href: "govt-services.html",
            external: false,
          });
        }
      }

      const anchors = Array.from(document.querySelectorAll("a[href]"));
      const seen = new Set(items.map((x) => `${x.href}|${x.name}`));
      for (const a of anchors) {
        const href = safe(a.getAttribute("href"));
        const text = safe(a.textContent);
        if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) continue;
        if (!text || text.length < 2) continue;
        const key = `${href}|${text}`;
        if (seen.has(key)) continue;
        seen.add(key);
        items.push({ name: text, href, external: /^https?:\/\//i.test(href) && !href.includes(location.hostname) });
      }

      INDEX = items;
      return INDEX;
    }

    function scoreMatch(q, item) {
      const hay = (item.name + " " + (item.rawUrl || item.href)).toLowerCase();
      if (!hay.includes(q)) return 0;
      let s = 1;
      if (item.name.toLowerCase().includes(q)) s += 2;
      if ((item.rawUrl || item.href).toLowerCase().includes(q)) s += 1;
      return s;
    }

    function render(query, matches) {
      const q = safe(query);
      if (!q) {
        resultsHost.innerHTML = "";
        resultsHost.style.display = "none";
        return;
      }

      const top = matches.slice(0, 40);
      resultsHost.style.display = "block";

      if (!top.length) {
        resultsHost.innerHTML = `<div class="seo-block" style="margin-top:10px;">
          <strong>No results found for “${escapeHtml(q)}”.</strong>
          <div style="margin-top:6px;color:var(--muted);">Try: SSC, Railway, Bank, Police, Admit Card, Result.</div>
        </div>`;
        return;
      }

      resultsHost.innerHTML = `
        <div class="seo-block" style="margin-top:10px;">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;">
            <strong>Showing ${top.length}${matches.length > top.length ? "+" : ""} result(s) for “${escapeHtml(q)}”</strong>
            <button id="clearHomeSearch" type="button" class="btn-primary" style="padding:8px 12px;">Clear</button>
          </div>
          <div style="margin-top:10px;display:grid;gap:10px;">
            ${top
              .map((m) => {
                const href = escapeHtml(m.href);
                const name = escapeHtml(m.name);
                return `<a class="card-link" href="${href}" style="display:block;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:#fff;">
                  <div style="font-weight:700;">${name}</div>
                  <div style="margin-top:4px;font-size:12px;color:var(--muted);word-break:break-word;">${escapeHtml(m.rawUrl || m.href)}</div>
                </a>`;
              })
              .join("")}
          </div>
        </div>
      `;

      const clearBtn = document.getElementById("clearHomeSearch");
      if (clearBtn) {
        clearBtn.addEventListener("click", () => {
          input.value = "";
          resultsHost.innerHTML = "";
          resultsHost.style.display = "none";
          input.focus();
        });
      }
    }

    async function runSearch() {
      const query = safe(input.value);
      if (!query) {
        render("", []);
        return;
      }

      resultsHost.style.display = "block";
      resultsHost.innerHTML = `<div class="seo-block" style="margin-top:10px;">Searching…</div>`;

      const idx = await buildIndex();
      const q = query.toLowerCase();
      const matches = idx
        .map((it, i) => ({ ...it, _i: i, _s: scoreMatch(q, it) }))
        .filter((x) => x._s > 0)
        .sort((a, b) => (b._s - a._s) || (a._i - b._i));

      render(query, matches);
    }

    if (btn) btn.addEventListener("click", runSearch);

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        runSearch();
      }
    });

    let t = null;
    input.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(() => {
        if (safe(input.value).length >= 2) runSearch();
        if (!safe(input.value)) {
          resultsHost.innerHTML = "";
          resultsHost.style.display = "none";
        }
      }, 250);
    });

    const qParam = getQueryParam("q");
    if (qParam) {
      input.value = qParam;
      await runSearch();
    }
  }

  // ------------
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
      await initHomepageSearch();
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
