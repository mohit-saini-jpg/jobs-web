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

  // Used across site for external links inside view.html wrapper
  function openInternal(url, name) {
    const u = normalizeUrl(url);
    return `view.html?url=${encodeURIComponent(u)}&name=${encodeURIComponent(name)}`;
  }

  // ✅ Tools page header uses onclick="goBack()" (tools.html)
  window.goBack = () => {
    if (window.history.length > 1) window.history.back();
    else window.location.href = "index.html";
  };

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
  // ✅ CATEGORY PAGE (category.html?group=...)
  // Restores the same content/links that were previously shown on the homepage sections.
  // Data source priority:
  //   1) jobs.json (if present)
  //   2) dynamic-sections.json (fallback)
  // No new content is created — we only render existing data.
  // ---------------------------
  async function initCategoryPage() {
    if (page !== "category.html") return;

    const titleEl = $("#categoryTitle");
    const descEl = $("#categoryDesc");
    const filterEl = $("#categoryFilter");
    const clearBtn = $("#clearCategoryFilter");
    const gridEl = $("#categoryGrid");
    const emptyEl = $("#categoryEmpty");

    if (!titleEl || !gridEl || !emptyEl) return;

    const params = new URLSearchParams(location.search || "");
    const group = safe(params.get("group")).toLowerCase();

    const groupMeta = {
      study: { title: "Study wise jobs", desc: "Browse jobs by qualification level." },
      popular: { title: "Popular job categories", desc: "Top job categories people search for." },
      state: { title: "State wise jobs", desc: "Government jobs by state." },
      admissions: { title: "Admissions", desc: "Admissions and entrance related updates." },
      "admit-result": { title: "Admit Card / Result / Answer Key / Syllabus", desc: "Admit cards, results, answer keys and syllabus updates." },
      khabar: { title: "Latest Khabar", desc: "Latest news and updates." },
      "study-material": { title: "Study Material & Top Courses", desc: "Study notes, courses and preparation material." },
    };

    const meta = groupMeta[group] || { title: "Category", desc: "" };
    titleEl.textContent = meta.title;
    if (descEl) descEl.textContent = meta.desc;

    async function tryFetchJson(path) {
      try {
        const r = await fetch(path, { cache: "no-store" });
        if (!r.ok) return null;
        return await r.json();
      } catch (_) {
        return null;
      }
    }

    // Decide whether a URL is internal to this site (should not be wrapped in view.html)
    function isInternalLink(url) {
      const u = safe(url);
      if (!u) return false;
      if (u.startsWith("#") || u.startsWith("?")) return true;
      if (u.startsWith("/") || u.startsWith("./") || u.startsWith("../")) return true;
      if (u.endsWith(".html") || /\.html[?#]/i.test(u)) return true;
      if (/^(https?:)?\/\//i.test(u)) return false;
      return true;
    }

    function hrefForItem(url, name) {
      const u = safe(url);
      const n = safe(name) || "Open";
      if (!u) return "#";
      if (isInternalLink(u)) return u; // internal pages should open normally
      return openInternal(u, n); // external links use view.html wrapper
    }

    function normalizeList(list) {
      return (list || [])
        .map((it) => ({
          name: safe(it?.name || it?.title || it?.label),
          url: it?.url || it?.link || it?.href || it?.path || "",
          date: safe(it?.date || it?.lastDate || it?.last_date),
          external: it?.external === true,
        }))
        .filter((it) => it.name && it.url);
    }

    // 1) Try jobs.json
    let items = [];
    const jobsJson = await tryFetchJson("jobs.json");
    if (jobsJson) {
      if (jobsJson.groups && typeof jobsJson.groups === "object" && Array.isArray(jobsJson.groups[group])) {
        items = normalizeList(jobsJson.groups[group]);
      } else if (Array.isArray(jobsJson[group])) {
        items = normalizeList(jobsJson[group]);
      } else if (Array.isArray(jobsJson)) {
        const byGroup = jobsJson.filter((x) => safe(x.group).toLowerCase() === group);
        if (byGroup.length && Array.isArray(byGroup[0].items)) {
          items = normalizeList(byGroup[0].items);
        } else if (byGroup.length) {
          items = normalizeList(byGroup);
        }
      } else if (typeof jobsJson === "object") {
        const keyCandidates = [
          group,
          group.replace("-", "_"),
          group.replace("-", ""),
          `group_${group}`,
        ];
        for (const k of keyCandidates) {
          const v = jobsJson[k];
          if (Array.isArray(v)) {
            items = normalizeList(v);
            break;
          }
          if (v && Array.isArray(v.items)) {
            items = normalizeList(v.items);
            break;
          }
        }
      }
    }

    // 2) Fallback to dynamic-sections.json (if needed)
    if (!items.length) {
      const ds = await tryFetchJson("dynamic-sections.json");
      if (ds && Array.isArray(ds.sections)) {
        const sections = ds.sections;

        const pickByTitle = (needles) => {
          const re = new RegExp(needles.map(escRE).join("|"), "i");
          return sections.find((s) => re.test(safe(s.title)));
        };

        const sec =
          group === "study"
            ? pickByTitle(["Study wise"])
            : group === "popular"
            ? pickByTitle(["Popular"])
            : group === "state"
            ? pickByTitle(["State wise"])
            : group === "admissions"
            ? pickByTitle(["Admissions"])
            : group === "admit-result"
            ? pickByTitle(["Admit", "Result", "Answer Key", "Syllabus"])
            : group === "khabar"
            ? pickByTitle(["Khabar", "News"])
            : group === "study-material"
            ? pickByTitle(["Study Material", "Courses"])
            : null;

        if (sec && Array.isArray(sec.items)) items = normalizeList(sec.items);
      }
    }

    function render(list) {
      gridEl.innerHTML = "";

      if (!list.length) {
        emptyEl.hidden = false;
        return;
      }
      emptyEl.hidden = true;

      list.forEach((it) => {
        const a = document.createElement("a");
        a.className = "section-link";

        const href = hrefForItem(it.url, it.name);
        a.href = href;

        // Open new tab only if it's truly external and not wrapped
        const isExternalRaw = /^(https?:)?\/\//i.test(safe(it.url)) || /^www\./i.test(safe(it.url));
        const wrapped = href.startsWith("view.html?");
        if (isExternalRaw && !wrapped) {
          a.target = "_blank";
          a.rel = "noopener";
        }

        a.innerHTML = `
          <div class="t">${it.name}</div>
          ${it.date ? `<div class="d">${it.date}</div>` : `<div class="d">Open official link</div>`}
        `;
        gridEl.appendChild(a);
      });
    }

    const applyFilter = () => {
      const q = safe(filterEl?.value).toLowerCase();
      if (!q) return render(items);
      render(items.filter((x) => x.name.toLowerCase().includes(q)));
    };

    if (filterEl) filterEl.addEventListener("input", applyFilter);
    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        if (filterEl) filterEl.value = "";
        applyFilter();
      });
    }

    render(items);
  }

  // ---------------------------
  // ✅ Tools page
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

    try {
      categoryButtons.forEach((btn) => {
        const key = safe(btn.getAttribute("data-category"));
        const n = Array.isArray(toolsData[key]) ? toolsData[key].length : null;
        if (typeof n === "number") {
          const countEl = btn.querySelector(".text-sm.text-gray-500.mt-2");
          if (countEl) countEl.textContent = `${n} tools available`;
        }
      });
    } catch (_) {}

    showCategories();
  }

  // ---------------------------
  // ✅ CSC Services (govt-services.html) — Supabase insert into csc_service_requests
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

      const first = $("input, select, textarea", form);
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

      if (!fullName || !phone || phone.length < 8 || !msg) {
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

  // Boot
  document.addEventListener("DOMContentLoaded", async () => {
    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    initFAQ();

    if (page === "index.html" || page === "") {
      await renderHomepageSections();
    }

    // ✅ Restore dropdown subpages content (Jobs / Admissions / More)
    await initCategoryPage();

    // Tools page wiring (fix broken clicks)
    await initToolsPage();

    // Services page
    if (page === "govt-services.html") {
      ensureSupabaseClient().catch(() => {});
    }
    initCscModal();
    await renderServicesPage();
  });
})();
