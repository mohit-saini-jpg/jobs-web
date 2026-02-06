(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const safe = (v) => (v ?? "").toString().trim();
  const escRE = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  function normalizeUrl(raw) {
    const s = safe(raw);
    if (!s) return "#";
    if (/^(https?:)?\/\//i.test(s)) return s.startsWith("//") ? `https:${s}` : s;
    if (/^[a-z][a-z0-9+\-.]*:/i.test(s)) return s; // mailto:, tel:, etc.
    // treat as relative
    return s;
  }

  // ---- Offcanvas / Mobile menu ----
  function initOffcanvas() {
    const btn = $("#menu-toggle") || $(".menu-toggle") || $('[data-action="menu"]');
    const panel = $("#mobile-menu") || $(".mobile-menu") || $("#offcanvas") || $(".offcanvas");
    const overlay = $("#overlay") || $(".overlay");
    const closeBtn = $("#menu-close") || $(".menu-close") || $('[data-action="close-menu"]');

    if (!btn || !panel) return;

    const openClass = "is-open";
    const lockClass = "no-scroll";

    const open = () => {
      panel.classList.add(openClass);
      if (overlay) overlay.classList.add(openClass);
      document.body.classList.add(lockClass);
      btn.setAttribute("aria-expanded", "true");
    };

    const close = () => {
      panel.classList.remove(openClass);
      if (overlay) overlay.classList.remove(openClass);
      document.body.classList.remove(lockClass);
      btn.setAttribute("aria-expanded", "false");
    };

    const toggle = () => {
      if (panel.classList.contains(openClass)) close();
      else open();
    };

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      toggle();
    });

    if (closeBtn) {
      closeBtn.addEventListener("click", (e) => {
        e.preventDefault();
        close();
      });
    }

    if (overlay) {
      overlay.addEventListener("click", () => close());
    }

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });
  }

  // ---- Desktop dropdowns ----
  function initDropdowns() {
    const triggers = $$(".has-dropdown, .dropdown, [data-dropdown]");
    if (!triggers.length) return;

    const OPEN = "open";
    const CLOSE_DELAY = 180;

    triggers.forEach((wrap) => {
      const btn =
        wrap.querySelector("button, a") ||
        wrap.querySelector('[data-role="dropdown-trigger"]') ||
        wrap;
      const menu =
        wrap.querySelector(".dropdown-menu, .submenu, ul") ||
        wrap.querySelector('[data-role="dropdown-menu"]');

      if (!btn || !menu) return;

      let t = null;

      const open = () => {
        clearTimeout(t);
        wrap.classList.add(OPEN);
        btn.setAttribute("aria-expanded", "true");
      };

      const close = () => {
        clearTimeout(t);
        t = setTimeout(() => {
          wrap.classList.remove(OPEN);
          btn.setAttribute("aria-expanded", "false");
        }, CLOSE_DELAY);
      };

      const closeNow = () => {
        clearTimeout(t);
        wrap.classList.remove(OPEN);
        btn.setAttribute("aria-expanded", "false");
      };

      wrap.addEventListener("mouseenter", open);
      wrap.addEventListener("mouseleave", close);

      btn.addEventListener("click", (e) => {
        // click should toggle (for touch devices / keyboard users)
        if (wrap.classList.contains(OPEN)) {
          e.preventDefault();
          closeNow();
        } else {
          e.preventDefault();
          open();
        }
      });

      btn.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeNow();
        if (e.key === "ArrowDown") open();
      });

      document.addEventListener("click", (e) => {
        if (!wrap.contains(e.target)) closeNow();
      });

      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeNow();
      });
    });
  }

  // ---- FAQ toggles ----
  function initFAQ() {
    const items = $$(".faq-item, .faq");
    if (!items.length) return;
    items.forEach((it) => {
      const btn = it.querySelector("button, .faq-question");
      const panel = it.querySelector(".faq-panel, .faq-answer");
      if (!btn || !panel) return;

      btn.addEventListener("click", () => {
        const isOpen = !panel.hidden;
        panel.hidden = isOpen;
      });
    });
  }

  // ---- Header links JSON ----
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
      socials.forEach((l) => {
        const a = document.createElement("a");
        a.href = normalizeUrl(l.link || l.url || "#");
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = l.name || "Social";
        footerSocial.appendChild(a);
      });
    }
  }

  function openInternal(url, name) {
    const u = normalizeUrl(url);
    return `view.html?url=${encodeURIComponent(u)}&name=${encodeURIComponent(name)}`;
  }

  // ---- Homepage dynamic sections ----
  async function renderHomepageSections() {
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
      const title = safe(sec.title || sec.name);
      const items = Array.isArray(sec.items) ? sec.items : Array.isArray(sec.links) ? sec.links : [];
      if (!title || !items.length) return;

      const box = document.createElement("section");
      box.className = "dynamic-section";

      const h = document.createElement("h3");
      h.textContent = title;
      box.appendChild(h);

      const list = document.createElement("div");
      list.className = "dynamic-list";

      items.forEach((it) => {
        const nm = safe(it.name || it.title);
        const url = safe(it.url || it.link || it.href);
        if (!nm && !url) return;

        const a = document.createElement("a");
        a.className = "dynamic-item";
        a.textContent = nm || url;

        if (url) {
          const external = /^https?:\/\//i.test(url);
          a.href = external ? openInternal(url, nm || url) : url;
        } else {
          a.href = `view.html?section=${encodeURIComponent(nm)}`;
        }
        list.appendChild(a);
      });

      box.appendChild(list);
      wrap.appendChild(box);
    });
  }

  // ---- CSC modal (kept as-is) ----
  function initCscModal() {
    const modal = $("#csc-modal");
    if (!modal) return;

    const closeBtns = $$(".csc-close", modal);
    const titleEl = $("#csc-service-title", modal);
    const form = $("#csc-form", modal);

    const open = () => {
      modal.classList.add("open");
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("no-scroll");
    };

    const close = () => {
      modal.classList.remove("open");
      modal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("no-scroll");
    };

    closeBtns.forEach((b) => b.addEventListener("click", (e) => {
      e.preventDefault();
      close();
    }));

    modal.addEventListener("click", (e) => {
      if (e.target === modal) close();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });

    function openModal({ name }) {
      if (titleEl) titleEl.textContent = name || "Service Request";
      if (form) form.reset();
      open();
    }

    // Bind all services that have data-csc-service
    $$(".csc-service, [data-csc-service]").forEach((el) => {
      el.addEventListener("click", (e) => {
        const nm = el.getAttribute("data-csc-service") || el.textContent;
        if (!nm) return;
        e.preventDefault();
        openModal({ name: nm });
      });
    });

    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        // Your existing CSC submit logic remains wherever you had it earlier.
        // (This script only restores navigation/content rendering + header/footer consistency.)
        close();
      });
    }
  }

  // ---- Services page render (kept) ----
  async function renderServicesPage() {
    const list = $("#services-list");
    if (!list) return;

    let data = [];
    try {
      const r = await fetch("services.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    list.innerHTML = "";

    (Array.isArray(data) ? data : []).forEach((s) => {
      const name = safe(s.name);
      const url = safe(s.url);
      if (!name) return;

      const a = document.createElement("a");
      a.href = "#";
      a.className = "service-item";
      a.textContent = name;

      a.addEventListener("click", (e) => {
        e.preventDefault();
        // open modal instead of linking away
        const el = document.querySelector(`[data-csc-service="${escRE(name)}"]`);
        if (el) el.click();
        else {
          // fallback: open modal directly if present
          const modal = $("#csc-modal");
          if (modal) {
            const t = $("#csc-service-title", modal);
            if (t) t.textContent = name;
            modal.classList.add("open");
          } else if (url) {
            location.href = openInternal(url, name);
          }
        }
      });

      list.appendChild(a);
    });
  }

  async function syncHeaderFooterWithHome() {
    // Make every page use EXACT same header/footer as homepage.
    // We copy markup from index.html at runtime (same-origin fetch).
    if (page === "index.html" || page === "" || page === "index") return;

    const curHeader = document.querySelector("header");
    const curFooter = document.querySelector("footer");

    try {
      const r = await fetch("index.html", { cache: "no-store" });
      if (!r.ok) return;

      const html = await r.text();
      const doc = new DOMParser().parseFromString(html, "text/html");

      const homeHeader = doc.querySelector("header");
      const homeFooter = doc.querySelector("footer");

      if (homeHeader) {
        const cloned = homeHeader.cloneNode(true);
        if (curHeader) curHeader.replaceWith(cloned);
        else document.body.insertAdjacentElement("afterbegin", cloned);
      }

      if (homeFooter) {
        const cloned = homeFooter.cloneNode(true);
        if (curFooter) curFooter.replaceWith(cloned);
        else document.body.insertAdjacentElement("beforeend", cloned);
      }
    } catch (_) {}
  }

  function qsParam(name) {
    try {
      const sp = new URLSearchParams(location.search || "");
      return safe(sp.get(name));
    } catch (_) {
      return "";
    }
  }

  async function loadJson(path, fallback) {
    try {
      const r = await fetch(path, { cache: "no-store" });
      if (r.ok) return await r.json();
    } catch (_) {}
    return fallback;
  }

  function ensureContainer(selectors, createAfterEl) {
    const found = selectors.map((s) => document.querySelector(s)).find(Boolean);
    if (found) return found;

    const div = document.createElement("div");
    div.id = "js-generated";
    div.style.width = "100%";
    if (createAfterEl && createAfterEl.parentNode) {
      createAfterEl.insertAdjacentElement("afterend", div);
    } else {
      document.body.appendChild(div);
    }
    return div;
  }

  function normalizeSectionKey(s) {
    return safe(s).toLowerCase().replace(/\s+/g, " ").trim();
  }

  function sectionMatchesTitle(group, title) {
    const g = normalizeSectionKey(group);
    const t = normalizeSectionKey(title);
    if (!g || !t) return false;

    const map = {
      study: ["study", "education", "qualification", "class"],
      popular: ["popular", "category", "categories"],
      state: ["state", "states"],
      admissions: ["admission", "admissions", "admit card", "answer key", "syllabus", "result"],
      more: ["khabar", "news", "study material", "courses", "more"],
    };

    const keys = map[g] || [g];
    return keys.some((k) => t.includes(k));
  }

  function renderLinkList(items, listEl) {
    listEl.innerHTML = "";
    items.forEach((it) => {
      const name = safe(it.name || it.title || it.label || it.text);
      const url = safe(it.url || it.link || it.href);

      if (!name && !url) return;

      const a = document.createElement("a");
      a.className = "result-link";
      a.textContent = name || url;

      if (url) {
        const external = /^https?:\/\//i.test(url);
        a.href = external ? openInternal(url, name || url) : url;
      } else {
        a.href = `view.html?section=${encodeURIComponent(name)}`;
      }

      listEl.appendChild(a);
    });
  }

  async function initToolsPage() {
    const grid = document.getElementById("tools-grid");
    if (!grid) return;

    const data = await loadJson("tools.json", {});
    const groups = Object.keys(data || {});
    if (!groups.length) return;

    grid.innerHTML = "";

    groups.forEach((groupName) => {
      const items = Array.isArray(data[groupName]) ? data[groupName] : [];
      items.forEach((tool) => {
        const name = safe(tool.name);
        const url = safe(tool.url);
        const icon = safe(tool.icon);

        const card = document.createElement("a");
        card.className =
          "block p-4 rounded-lg border border-gray-200 hover:shadow-md transition bg-white";
        card.href = normalizeUrl(url || "#");
        card.target = "_blank";
        card.rel = "noopener";

        const title = document.createElement("div");
        title.className = "flex items-center gap-3";

        const i = document.createElement("i");
        if (icon) i.className = icon;
        title.appendChild(i);

        const span = document.createElement("span");
        span.className = "font-semibold";
        span.textContent = name || "Tool";
        title.appendChild(span);

        card.appendChild(title);

        const meta = document.createElement("div");
        meta.className = "text-sm text-gray-500 mt-2";
        meta.textContent = groupName.toUpperCase();
        card.appendChild(meta);

        grid.appendChild(card);
      });
    });
  }

  async function initCategoryPage() {
    if (page !== "category.html") return;

    const group = qsParam("group") || qsParam("g");
    const q = qsParam("q");

    const data = await loadJson("dynamic-sections.json", { sections: [] });
    const sections = Array.isArray(data.sections) ? data.sections : [];

    const matched = sections.filter((s) => sectionMatchesTitle(group, s.title || s.name || ""));
    const source = matched.length ? matched : sections;

    const h1 = Array.from(document.querySelectorAll("h1")).find((x) =>
      /category/i.test(safe(x.textContent))
    );
    const list = ensureContainer(
      ["#category-results", "#results", "#category-list", "#list", "#js-generated"],
      h1
    );

    let items = [];
    source.forEach((s) => {
      const arr = Array.isArray(s.items) ? s.items : Array.isArray(s.links) ? s.links : [];
      arr.forEach((it) => items.push(it));
    });

    if (q) {
      const qq = normalizeSectionKey(q);
      items = items.filter((it) => normalizeSectionKey(it.name || it.title || "").includes(qq));
    }

    if (!items.length) {
      list.innerHTML = '<div class="text-sm text-gray-600">No results found.</div>';
      return;
    }

    renderLinkList(
      items.map((it) => {
        const name = safe(it.name || it.title);
        let url = safe(it.url || it.link);
        if (!url && name) url = `view.html?section=${encodeURIComponent(name)}`;
        return { name, url };
      }),
      list
    );
  }

  async function initViewPage() {
    if (page !== "view.html") return;

    const url = qsParam("url");
    const name = qsParam("name");
    const section = qsParam("section");

    const iframe = document.querySelector("iframe");
    const openBtn = Array.from(document.querySelectorAll("a,button")).find((el) =>
      /open in new tab/i.test(safe(el.textContent))
    );

    if (url) {
      if (iframe) iframe.src = normalizeUrl(url);
      if (openBtn && openBtn.tagName.toLowerCase() === "a") openBtn.href = normalizeUrl(url);
      if (name) document.title = `${name} - Top Sarkari Jobs`;
      return;
    }

    const targetSection = section || name;
    const list = ensureContainer(
      ["#links-list", "#links", "#results", ".links-list", ".results-list", "#js-generated"],
      document.querySelector("h2")
    );

    const countEl = Array.from(document.querySelectorAll("p,div,span")).find((el) =>
      /^showing\s+\d+\s+links\./i.test(safe(el.textContent))
    );
    const loadingEl = Array.from(document.querySelectorAll("*")).find((el) => {
      const t = safe(el.textContent).toLowerCase();
      return t.includes("loading") && t.includes("please wait");
    });

    const jobsData = await loadJson("jobs.json", []);
    let items = [];

    if (Array.isArray(jobsData) && jobsData.length) {
      const key = normalizeSectionKey(targetSection);
      items = jobsData
        .filter((j) => {
          const fields = [
            j.section,
            j.category,
            j.group,
            j.tag,
            j.tags,
            j.title,
            j.name,
            j.label,
          ]
            .map((v) => safe(Array.isArray(v) ? v.join(" ") : v))
            .join(" ");
          return normalizeSectionKey(fields).includes(key);
        })
        .map((j) => ({
          name: safe(j.title || j.name || j.label || targetSection),
          url: safe(j.url || j.link || j.href || ""),
        }));
    }

    if (!items.length) {
      const ds = await loadJson("dynamic-sections.json", { sections: [] });
      const sections = Array.isArray(ds.sections) ? ds.sections : [];
      const key = normalizeSectionKey(targetSection);
      const sec = sections.find((s) => normalizeSectionKey(s.title || s.name || "").includes(key));
      const arr = sec
        ? Array.isArray(sec.items)
          ? sec.items
          : Array.isArray(sec.links)
          ? sec.links
          : []
        : [];
      items = arr.map((it) => ({
        name: safe(it.name || it.title),
        url: safe(it.url || it.link || ""),
      }));
    }

    if (loadingEl) loadingEl.remove();

    if (!items.length) {
      list.innerHTML =
        '<div class="text-sm text-gray-600">We couldn’t find what to display. Please go back and open the section again.</div>';
      if (countEl) countEl.textContent = "Showing 0 links.";
      return;
    }

    if (countEl) countEl.textContent = `Showing ${items.length} links.`;

    renderLinkList(
      items.map((it) => ({
        name: it.name,
        url: it.url || `view.html?section=${encodeURIComponent(it.name)}`,
      })),
      list
    );
  }

  // Boot
  document.addEventListener("DOMContentLoaded", async () => {
    await syncHeaderFooterWithHome();
    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    initFAQ();

    if (page === "index.html" || page === "") {
      await renderHomepageSections();
    }

    initCscModal();
    await renderServicesPage();
    await initToolsPage();
    await initCategoryPage();
    await initViewPage();
  });
})();
