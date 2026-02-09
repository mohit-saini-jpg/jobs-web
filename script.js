/* FULL UPDATED script.js (homepage search fixed) */

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

  // ✅ Inject same homepage header/footer everywhere (Results now, other pages later)
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
        a.className = "mobile-link";
        a.href = normalizeUrl(l.link || l.url || "#");
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = l.name || "Link";
        mobile.appendChild(a);
      });
    }

    if (footerSocial) {
      footerSocial.innerHTML = "";
      socials.forEach((l) => {
        const a = document.createElement("a");
        a.href = normalizeUrl(l.link || l.url || "#");
        a.target = "_blank";
        a.rel = "noopener";
        a.innerHTML = `<i class="${l.icon || "fa-solid fa-link"}"></i>`;
        footerSocial.appendChild(a);
      });
    }
  }

  // ---------------------------
  // Offcanvas menu
  // ---------------------------
  function initOffcanvas() {
    const btn = $("#menuBtn");
    const menu = $("#mobileMenu");
    const overlay = $("#menuOverlay");
    const closeBtn = $("#closeMenuBtn");
    if (!btn || !menu || !overlay) return;

    const open = () => {
      menu.classList.add("open");
      overlay.classList.add("open");
      btn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
    };

    const close = () => {
      menu.classList.remove("open");
      overlay.classList.remove("open");
      btn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
    };

    const toggle = () => {
      if (menu.classList.contains("open")) close();
      else open();
    };

    btn.addEventListener("click", toggle);
    overlay.addEventListener("click", close);
    if (closeBtn) closeBtn.addEventListener("click", close);

    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth >= 980) close();
    });
  }

  // ---------------------------
  // Desktop dropdowns (hover-safe)
  // ---------------------------
  function initDropdowns() {
    const dds = $$("[data-dd]");
    if (!dds.length) return;

    dds.forEach((dd) => {
      const btn = dd.querySelector(".nav-dd-btn");
      const menu = dd.querySelector(".nav-dd-menu");
      if (!btn || !menu) return;

      let closeTimer = null;

      const open = () => {
        clearTimeout(closeTimer);
        dd.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
      };

      const close = () => {
        dd.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
      };

      const closeDelayed = () => {
        clearTimeout(closeTimer);
        closeTimer = setTimeout(close, 150);
      };

      btn.addEventListener("mouseenter", open);
      menu.addEventListener("mouseenter", open);

      btn.addEventListener("mouseleave", closeDelayed);
      menu.addEventListener("mouseleave", closeDelayed);

      btn.addEventListener("click", (e) => {
        // Mobile will use offcanvas; this is only for desktop click toggle safety
        e.preventDefault();
        if (dd.classList.contains("open")) close();
        else open();
      });

      document.addEventListener("click", (e) => {
        if (!dd.contains(e.target)) close();
      });

      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") close();
      });
    });
  }

  // ---------------------------
  // FAQ
  // ---------------------------
  function initFAQ() {
    const btns = $$(".faq-btn");
    btns.forEach((b) => {
      b.addEventListener("click", () => {
        const expanded = b.getAttribute("aria-expanded") === "true";
        b.setAttribute("aria-expanded", expanded ? "false" : "true");
        const panel = b.nextElementSibling;
        if (panel) panel.hidden = expanded;
      });
    });
  }

  // ---------------------------
  // Homepage dynamic sections
  // ---------------------------
  async function renderHomepageSections() {
    const host = $("#dynamic-sections");
    if (!host) return;

    let data = null;
    try {
      const r = await fetch("dynamic-sections.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const sections = (data && Array.isArray(data.sections) ? data.sections : []) || [];
    host.innerHTML = "";

    sections.forEach((sec) => {
      const title = safe(sec.title) || "Section";
      const items = Array.isArray(sec.items) ? sec.items : [];

      const card = document.createElement("section");
      card.className = "duo-card";

      const h = document.createElement("div");
      h.className = "duo-head";
      h.innerHTML = `<h3>${title}</h3>`;
      card.appendChild(h);

      const list = document.createElement("div");
      list.className = "section-list";

      items.forEach((it) => {
        const name = safe(it.name);
        const url = safe(it.url || it.link);
        if (!name || !url) return;

        const a = document.createElement("a");
        a.className = "section-link";

        const external = !!it.external;
        a.href = external ? normalizeUrl(url) : openInternal(url, name);
        if (external) {
          a.target = "_blank";
          a.rel = "noopener";
        }

        a.innerHTML = `
          <div class="t">${name}</div>
          <div class="d">${external ? "Open" : "View details"}</div>
        `;
        list.appendChild(a);
      });

      card.appendChild(list);
      host.appendChild(card);
    });
  }

  async function renderHomeQuickLinks() {
    const host = $("#home-quick-links");
    if (!host) return;

    // Optional section; if not present, do nothing
    let data = null;
    try {
      const r = await fetch("dynamic-sections.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const sections = (data && Array.isArray(data.sections) ? data.sections : []) || [];
    const flat = [];
    sections.forEach((s) => {
      (Array.isArray(s.items) ? s.items : []).forEach((it) => {
        const name = safe(it.name);
        const url = safe(it.url || it.link);
        if (name && url) flat.push({ name, url, external: !!it.external });
      });
    });

    if (!flat.length) return;

    host.innerHTML = `
      <div class="seo-block">
        <h2 style="margin:0 0 8px;">Quick links</h2>
        <div class="section-list">
          ${flat
            .slice(0, 18)
            .map((x) => {
              const href = x.external ? normalizeUrl(x.url) : openInternal(x.url, x.name);
              const target = x.external ? ` target="_blank" rel="noopener"` : "";
              return `
                <a class="section-link" href="${href}"${target}>
                  <div class="t">${x.name}</div>
                  <div class="d">${x.external ? "Open" : "View details"}</div>
                </a>
              `;
            })
            .join("")}
        </div>
      </div>
    `;
  }

  function removeHomeMainPageCtaLinks() {
    // Removes the specific "Main Home Page" CTA lines from homepage sections, if present.
    // (keeps everything else unchanged)
    if (!(page === "index.html" || page === "")) return;
    const needles = ["Website का Main Home Page खोलने के लिए यहाँ क्लिक करें"];
    const links = $$("a");
    links.forEach((a) => {
      const t = safe(a.textContent);
      if (needles.some((n) => t.includes(n))) {
        const p = a.closest("p") || a;
        p.remove();
      }
    });
  }

  // ---------------------------
  // Homepage search (site-wide index)
  // ---------------------------
  function initHomepageSearch() {
    if (!(page === "index.html" || page === "")) return;

    const input = document.getElementById("siteSearchInput");
    const btn = document.getElementById("siteSearchBtn");
    const resultsHost = document.getElementById("searchResults");
    const openBtn = document.getElementById("openSearchBtn");

    if (!input || !btn || !resultsHost) return;

    const setMessage = (html) => {
      resultsHost.innerHTML = html || "";
    };

    const looksInternal = (u) =>
      /(^[./]|^\/|\.html(\?|#|$)|view\.html\?|search\.html\?|category\.html\?|result\.html\?|tools\.html\?|helpdesk\.html\?|govt-services\.html\?)/i.test(
        safe(u)
      );

    const makeHref = (url, name, externalFlag) => {
      const raw = safe(url);
      if (!raw) return "#";
      const external = externalFlag === true;

      if (external) return normalizeUrl(raw);
      return looksInternal(raw) ? normalizeUrl(raw) : openInternal(raw, name || "");
    };

    let index = null; // [{title, url, source, external}]
    const buildIndexOnce = async () => {
      if (index) return index;

      const out = [];

      const add = (title, url, source, external) => {
        const t = safe(title);
        const u = safe(url);
        if (!t || !u) return;
        out.push({ title: t, url: u, source: source || "", external: external === true });
      };

      const fetchJson = async (path) => {
        try {
          const r = await fetch(path, { cache: "no-store" });
          if (!r.ok) return null;
          return await r.json();
        } catch (_) {
          return null;
        }
      };

      const [dyn, jobs, tools, services] = await Promise.all([
        fetchJson("dynamic-sections.json"),
        fetchJson("jobs.json"),
        fetchJson("tools.json"),
        fetchJson("services.json"),
      ]);

      // dynamic-sections.json (homepage)
      if (dyn && Array.isArray(dyn.sections)) {
        dyn.sections.forEach((sec) => {
          const secTitle = safe(sec.title);
          const items = Array.isArray(sec.items) ? sec.items : [];
          items.forEach((it) => add(it.name, it.url || it.link, secTitle || "Homepage", !!it.external));
        });
      }

      // jobs.json (dropdown category data)
      const harvestJobArray = (arr, label) => {
        if (!Array.isArray(arr)) return;
        arr.forEach((it) => {
          if (it && typeof it === "object") {
            if (safe(it.name) && safe(it.url)) add(it.name, it.url, label, !!it.external);
          }
        });
      };
      if (jobs) {
        harvestJobArray(jobs.top_jobs, "Jobs");
        harvestJobArray(jobs.left_jobs, "Jobs");
        harvestJobArray(jobs.right_jobs, "Jobs");
      }

      // tools.json
      if (tools && typeof tools === "object") {
        if (Array.isArray(tools.categories)) {
          tools.categories.forEach((cat) => {
            const label = safe(cat.title) || "Tools";
            (Array.isArray(cat.items) ? cat.items : []).forEach((t) =>
              add(t.name, t.url || t.link, label, !!t.external)
            );
          });
        } else {
          Object.keys(tools).forEach((k) => {
            const list = Array.isArray(tools[k]) ? tools[k] : [];
            list.forEach((t) => add(t.name, t.url || t.link, "Tools", !!t.external));
          });
        }
      }

      // services.json (CSC Services)
      if (services) {
        const list = Array.isArray(services.services) ? services.services : Array.isArray(services) ? services : [];
        list.forEach((s) => {
          const nm = safe(s.name || s.service);
          if (!nm) return;
          // services open via CSC page modal; still searchable as “CSC Services”
          add(nm, "govt-services.html", "CSC Services", false);
        });
      }

      // De-duplicate by (title+url)
      const seen = new Set();
      index = out.filter((x) => {
        const key = (x.title + "||" + x.url).toLowerCase();
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });

      return index;
    };

    const highlight = (text, q) => {
      const t = safe(text);
      const qq = safe(q);
      if (!t || !qq) return t;
      const re = new RegExp(escRE(qq), "ig");
      return t.replace(re, (m) => `<mark>${m}</mark>`);
    };

    const runSearch = async () => {
      const q = safe(input.value);
      if (!q) {
        setMessage("");
        return;
      }

      setMessage(`<div class="mini-links" style="margin-top:10px;opacity:.85">Searching…</div>`);

      const data = await buildIndexOnce();
      const qlc = q.toLowerCase();

      const matches = data
        .map((x) => {
          const t = x.title.toLowerCase();
          const s = (x.source || "").toLowerCase();
          let score = 0;
          if (t.includes(qlc)) score += 5;
          if (s.includes(qlc)) score += 1;
          qlc.split(/\s+/).forEach((tok) => {
            if (!tok) return;
            if (t.includes(tok)) score += 2;
            if (s.includes(tok)) score += 0.5;
          });
          return { ...x, score };
        })
        .filter((x) => x.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 40);

      if (!matches.length) {
        setMessage(
          `<div class="seo-block" style="margin-top:12px;"><strong>No results found.</strong><div style="margin-top:6px;opacity:.8;">Try a different keyword.</div></div>`
        );
        return;
      }

      const html = `
        <div class="mini-links" style="margin-top:10px;opacity:.85;">
          Showing <strong>${matches.length}</strong> results for <strong>${q}</strong>
        </div>
        <div class="section-list" style="margin-top:10px;">
          ${matches
            .map((m) => {
              const href = makeHref(m.url, m.title, m.external);
              const tag = m.source ? `<div class="d">${safe(m.source)}</div>` : `<div class="d">Open</div>`;
              const target = m.external ? ` target="_blank" rel="noopener"` : "";
              return `
                <a class="section-link" href="${href}"${target}>
                  <div class="t">${highlight(m.title, q)}</div>
                  ${tag}
                </a>
              `;
            })
            .join("")}
        </div>
      `;
      setMessage(html);
    };

    btn.addEventListener("click", runSearch);

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        runSearch();
      }
    });

    let t = null;
    input.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(runSearch, 200);
    });

    if (openBtn) {
      openBtn.addEventListener("click", () => {
        const block = input.closest(".top-search") || input.closest("section") || input;
        if (block && block.scrollIntoView) block.scrollIntoView({ behavior: "smooth", block: "start" });
        input.focus();
      });
    }
  }

  // ---------------------------
  // Category pages (Jobs/Admissions/More dropdown subpages)
  // ---------------------------
  async function initCategoryPage() {
    if (page !== "category.html") return;

    const titleEl = $("#categoryTitle");
    const descEl = $("#categoryDesc");
    const crumbEl = $("#crumbText");
    const grid = $("#categoryGrid");
    const empty = $("#categoryEmpty");

    if (!grid) return;

    const params = new URLSearchParams(location.search);
    const group = safe(params.get("group") || "");

    let data = null;
    try {
      const r = await fetch("jobs.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const groups = (data && data.groups) || {};
    const meta = (groups && groups[group]) || null;

    const heading = safe((meta && meta.title) || group || "Category");
    const desc = safe((meta && meta.desc) || "");
    if (titleEl) titleEl.textContent = heading;
    if (crumbEl) crumbEl.textContent = heading;
    if (descEl) descEl.textContent = desc;

    const items = (meta && Array.isArray(meta.items) ? meta.items : []) || [];
    grid.innerHTML = "";

    const render = (list) => {
      grid.innerHTML = "";
      if (!list.length) {
        if (empty) empty.style.display = "block";
        return;
      }
      if (empty) empty.style.display = "none";

      list.forEach((it) => {
        const name = safe(it.name);
        const url = safe(it.url);
        if (!name || !url) return;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = normalizeUrl(url);
        a.innerHTML = `<div class="t">${name}</div><div class="d">Open</div>`;
        grid.appendChild(a);
      });
    };

    render(items);
  }

  // ---------------------------
  // Tools page
  // ---------------------------
  async function initToolsPage() {
    if (page !== "tools.html") return;

    const grid = $("#toolsGrid");
    if (!grid) return;

    let data = null;
    try {
      const r = await fetch("tools.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    const categories = data && Array.isArray(data.categories) ? data.categories : null;

    grid.innerHTML = "";

    if (categories) {
      categories.forEach((cat) => {
        const title = safe(cat.title) || "Tools";
        const items = Array.isArray(cat.items) ? cat.items : [];

        const block = document.createElement("section");
        block.className = "seo-block";
        block.innerHTML = `<h2 style="margin:0 0 10px;">${title}</h2>`;

        const list = document.createElement("div");
        list.className = "section-list";

        items.forEach((t) => {
          const name = safe(t.name);
          const url = safe(t.url || t.link);
          if (!name || !url) return;

          const a = document.createElement("a");
          a.className = "section-link";

          const external = !!t.external;
          a.href = external ? normalizeUrl(url) : openInternal(url, name);
          if (external) {
            a.target = "_blank";
            a.rel = "noopener";
          }

          a.innerHTML = `<div class="t">${name}</div><div class="d">${external ? "Open" : "View details"}</div>`;
          list.appendChild(a);
        });

        block.appendChild(list);
        grid.appendChild(block);
      });
    } else if (data && typeof data === "object") {
      Object.keys(data).forEach((k) => {
        const items = Array.isArray(data[k]) ? data[k] : [];
        if (!items.length) return;

        const block = document.createElement("section");
        block.className = "seo-block";
        block.innerHTML = `<h2 style="margin:0 0 10px;">${k}</h2>`;

        const list = document.createElement("div");
        list.className = "section-list";

        items.forEach((t) => {
          const name = safe(t.name);
          const url = safe(t.url || t.link);
          if (!name || !url) return;

          const a = document.createElement("a");
          a.className = "section-link";

          const external = !!t.external;
          a.href = external ? normalizeUrl(url) : openInternal(url, name);
          if (external) {
            a.target = "_blank";
            a.rel = "noopener";
          }

          a.innerHTML = `<div class="t">${name}</div><div class="d">${external ? "Open" : "View details"}</div>`;
          list.appendChild(a);
        });

        block.appendChild(list);
        grid.appendChild(block);
      });
    }
  }

  // ---------------------------
  // CSC Services modal + Supabase submit
  // ---------------------------
  let supabaseClient = null;

  async function ensureSupabaseClient() {
    if (supabaseClient) return supabaseClient;
    if (!window.supabase || !window.SUPABASE_URL || !window.SUPABASE_ANON_KEY) return null;
    supabaseClient = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY);
    return supabaseClient;
  }

  function initCscModal() {
    const modal = $("#cscModal");
    if (!modal) return;

    const overlay = $("#cscModalOverlay");
    const closeBtn = $("#closeCscModal");
    const form = $("#cscRequestForm");
    const title = $("#cscServiceTitle");

    const close = () => {
      modal.classList.remove("open");
      document.body.style.overflow = "";
    };

    const open = (payload) => {
      const nm = safe(payload && payload.name);
      if (title) title.textContent = nm || "Service Request";
      modal.classList.add("open");
      document.body.style.overflow = "hidden";

      // store on window for form submit
      modal.dataset.serviceName = nm || "";
      modal.dataset.serviceUrl = safe(payload && payload.url) || "";
    };

    if (overlay) overlay.addEventListener("click", close);
    if (closeBtn) closeBtn.addEventListener("click", close);

    window.__openCscModal = open;

    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const name = safe(modal.dataset.serviceName);
        const url = safe(modal.dataset.serviceUrl);

        const fullName = safe(form.querySelector("[name='full_name']")?.value);
        const phone = safe(form.querySelector("[name='phone']")?.value);
        const email = safe(form.querySelector("[name='email']")?.value);
        const city = safe(form.querySelector("[name='city']")?.value);
        const details = safe(form.querySelector("[name='details']")?.value);

        try {
          const client = await ensureSupabaseClient();
          if (!client) throw new Error("Supabase client not available");

          const { error } = await client.from("csc_service_requests").insert([
            {
              service_name: name,
              service_url: url,
              full_name: fullName,
              phone,
              email,
              city,
              details,
            },
          ]);

          if (error) throw error;

          alert("Request submitted successfully. We will contact you soon.");
          form.reset();
          close();
        } catch (err) {
          console.error("Submit error:", err);
          alert("Could not submit your request. Please check your connection and try again.");
        }
      });
    }
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
    initOffcanvas();
    initDropdowns();
    initFAQ();

    // Homepage content
    if (page === "index.html" || page === "") {
      await renderHomepageSections();
      await renderHomeQuickLinks();
      removeHomeMainPageCtaLinks();
      initHomepageSearch(); // ✅ FIX: homepage search now actually works
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
