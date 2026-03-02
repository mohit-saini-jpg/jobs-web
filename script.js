(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  const isToolsPage = location.pathname.includes("tools");

  const safe = (v) => (v ?? "").toString().trim();

  // Safely handles internal absolute URLs
  function normalizeUrl(raw) {
    const s = safe(raw);
    if (!s) return "";
    if (/^(https?:)?\/\//i.test(s) || /^(mailto:|tel:)/i.test(s)) return s;
    if (s.startsWith("#") || s.startsWith("?")) return s;
    if (s.startsWith("/") || s.includes(".html") || s.startsWith("./") || s.startsWith("../")) return s;
    return "https://" + s.replace(/^\/+/, "");
  }

  function isGarbageLink(item) {
    const text = (item.name || item.title || "").toLowerCase();
    return text.includes("main home page") || text.includes("website ka main");
  }

  function openInternal(url, name) {
    const u = normalizeUrl(url);
    return `view.html?url=${encodeURIComponent(u)}&name=${encodeURIComponent(name)}`;
  }

  window.goBack = () => {
    if (window.history.length > 1) window.history.back();
    else window.location.href = "index.html";
  };

  function buildMobileMenu() {
    const nav = document.querySelector(".offcanvas-nav");
    if (!nav) return;
    
    nav.innerHTML = `
      <a href="index.html">Home</a>
      <a href="result.html">Results</a>
      <a href="govt-services.html">CSC Services</a>
      <a href="tools.html">Tools</a>
      <a href="helpdesk.html">Helpdesk</a>

      <div class="offcanvas-group">
        <div class="offcanvas-group-title">Jobs</div>
        <a href="category.html?group=study">Study wise jobs</a>
        <a href="category.html?group=popular">Popular job categories</a>
        <a href="category.html?group=state">State wise jobs</a>
      </div>

      <div class="offcanvas-group">
        <div class="offcanvas-group-title">Admissions</div>
        <a href="category.html?group=admissions">Admissions</a>
        <a href="category.html?group=admit-result">Admit Card / Result / Answer Key / Syllabus</a>
      </div>

      <div class="offcanvas-group">
        <div class="offcanvas-group-title">More</div>
        <a href="category.html?group=khabar">Latest Khabar</a>
        <a href="category.html?group=study-material">Study Material & Top Courses</a>
      </div>

      <div class="offcanvas-cta" id="header-links-mobile"></div>
    `;
  }

  // MOBILE HEADER BUTTON INJECTION 
  function injectMobileHeaderBtns() {
    if (window.innerWidth > 980) return;
    const headerHost = document.getElementById("site-header") || document.querySelector(".site-header");
    if (!headerHost) return;

    const headerRow = headerHost.querySelector('.header-row');
    const headerActions = headerHost.querySelector('.header-actions');
    
    if (headerRow && headerActions && !document.getElementById('mobile-header-btns')) {
        const btns = document.createElement('div');
        btns.id = 'mobile-header-btns';
        btns.className = 'mobile-header-btns';
        btns.innerHTML = `
          <div class="mhb-row">
             <a href="helpdesk.html" class="mhb-btn">Helpdesk</a>
             <a href="index.html" class="mhb-btn">Home</a>
          </div>
          <a href="tools.html" class="mhb-btn mhb-full">Tools</a>
        `;
        headerRow.insertBefore(btns, headerActions);
    }
  }

  // SAFE OLD SEARCH HIDER - Strictly hides only the input rows and specific text
  function safeHideOldSearchBars() {
    if (window.innerWidth <= 980) {
        const oldInputs = document.querySelectorAll('#siteSearchInput, #sectionSearchInput');
        oldInputs.forEach(input => {
            const row = input.closest('.search-row');
            if (row && !row.classList.contains('mbs-row')) {
                row.style.setProperty('display', 'none', 'important');
            }
        });
        
        document.querySelectorAll('h1, h2, h3, p').forEach(el => {
            const txt = (el.textContent || "").trim();
            if (txt === "Search across Top Sarkari Jobs" || 
                txt === "Search jobs, results, admit cards, categories, CSC services and tools.") {
                el.style.setProperty('display', 'none', 'important');
            }
        });

        document.querySelectorAll('.top-search').forEach(ts => {
            ts.style.setProperty('display', 'none', 'important');
        });
    }
  }

  async function injectHeaderFooter() {
    let headerHost = document.getElementById("site-header");
    if (!headerHost) headerHost = document.querySelector(".site-header");

    const footerHost = document.getElementById("site-footer");
    
    if (headerHost && (!headerHost.querySelector(".brand") || headerHost.innerHTML.trim() === "")) {
        try {
          const r = await fetch("header.html", { cache: "no-store" });
          if (r.ok) {
              headerHost.innerHTML = await r.text();
              if (!headerHost.classList.contains("site-header")) {
                  headerHost.classList.add("site-header");
              }
          }
        } catch (_) {}
    }

    injectMobileHeaderBtns();

    if (footerHost && footerHost.innerHTML.trim() === "") {
        try {
          const r = await fetch("footer.html", { cache: "no-store" });
          if (r.ok) {
              footerHost.innerHTML = await r.text();
              if (!footerHost.classList.contains("site-footer")) footerHost.classList.add("site-footer");
          }
        } catch (_) {}
    }
  }

  // ✅ PERFECTED DESKTOP & MOBILE HEADER LINKS
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
        let linkName = safe(l.name);
        let linkUrl = safe(l.link || l.url || "#");

        // 1. Remove "Results" from Desktop View
        if (linkName.toLowerCase() === "results" || linkName.toLowerCase() === "result") {
            return; // Skip rendering
        }

        // 2. Replace "AI Helpdesk" with "Admit Card" & specific URL
        if (linkName.toLowerCase() === "ai helpdesk") {
            linkName = "Admit Card";
            linkUrl = "https://www.topsarkarijobs.com/view.html?section=Admit%20cards%20Exams%20Date";
        }

        const a = document.createElement("a");
        a.className = "nav-link";
        a.href = normalizeUrl(linkUrl);
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = linkName;
        desktop.appendChild(a);
      });
    }

    if (mobile) {
      mobile.innerHTML = "";
      links.forEach((l) => {
        let linkName = safe(l.name);
        let linkUrl = safe(l.link || l.url || "#");

        // Keep "Results" on mobile, just update URL
        if (linkName.toLowerCase() === "results" || linkName.toLowerCase() === "result") {
            linkUrl = "https://www.topsarkarijobs.com/view.html?section=results";
        }
        
        // Replace "AI Helpdesk" with "Admit Card" on mobile side menu
        if (linkName.toLowerCase() === "ai helpdesk") {
            linkName = "Admit Card";
            linkUrl = "https://www.topsarkarijobs.com/view.html?section=Admit%20cards%20Exams%20Date";
        }

        const a = document.createElement("a");
        a.href = normalizeUrl(linkUrl);
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = linkName;
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
      if (e.target.closest("a")) close();
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 980) close();
      safeHideOldSearchBars(); 
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
      const baseColor = safe(sec.color) || "#0284c7";
      const icon = safe(sec.icon) || "fa-solid fa-briefcase";

      const bgStyle = baseColor.includes("gradient") 
        ? `background: ${baseColor};` 
        : `background-color: ${baseColor}; background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.18) 0%, rgba(0, 0, 0, 0.15) 100%);`;

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
        <div class="section-head" style="${bgStyle} text-shadow: 0 1px 2px rgba(0,0,0,0.15); border-bottom: 1px solid rgba(0,0,0,0.05);">
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
        a.href = normalizeUrl(url); 
        if (external) { a.target = "_blank"; a.rel = "noopener"; }
        a.innerHTML = `<div class="t">${name}</div>${it.date ? `<div class="d">${safe(it.date)}</div>` : `<div class="d">Open official link</div>`}`;
        list.appendChild(a);
      });
      wrap.appendChild(card);
    });
  }

  async function renderHomeQuickLinks() {
    const isHome = (page === "index.html" || page === "");
    
    let wrap = document.getElementById("home-quicklinks-wrap");
    let host = document.getElementById("home-links");
    
    if (!wrap) {
      wrap = document.createElement("section");
      wrap.id = "home-quicklinks-wrap";
      wrap.className = isHome ? "home-quicklinks" : "home-quicklinks desktop-hidden";
      
      host = document.createElement("div");
      host.id = "home-links";
      host.className = "home-links";
      wrap.appendChild(host);
      
      const mainEl = document.getElementById("main") || document.querySelector("main") || document.body;
      if (mainEl && mainEl.parentNode) {
          mainEl.parentNode.insertBefore(wrap, mainEl);
      }
    }

    // ✅ FIXED DESKTOP PILLS CSS INJECTION - Brings back your properly padded buttons on desktop!
    if (!document.getElementById("home-quicklinks-style")) {
      const style = document.createElement("style");
      style.id = "home-quicklinks-style";
      style.textContent = `
        .home-quicklinks { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 0; }
        
        /* GLOBAL/DESKTOP VIEW FOR PILLS */
        .home-links { 
          display: flex; 
          flex-wrap: wrap; 
          gap: 10px; 
          align-items: center; 
          justify-content: center; 
          padding-bottom: 24px; 
        }
        
        .home-link-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 12px 24px;
          border-radius: 14px;
          color: #fff;
          font-weight: 800;
          font-size: 15px;
          text-decoration: none;
          line-height: 1.3;
          box-shadow: inset 0px 4px 6px rgba(255,255,255,0.35), inset 0px -4px 6px rgba(0,0,0,0.25), 0 4px 6px rgba(0,0,0,0.15);
          text-shadow: 0 1px 2px rgba(0,0,0,0.4);
          border: none;
          white-space: nowrap;
          transition: transform 0.2s ease, filter 0.2s ease;
        }
        
        .home-link-btn:hover {
          transform: translateY(-2px);
          filter: brightness(1.05);
        }
        .home-link-btn:active { transform: translateY(0); }
        
        /* Hides mobile UI on Desktop */
        @media (min-width: 981px) {
          .mobile-nav-grid, .mobile-bottom-search { display: none !important; }
        }

        /* MOBILE VIEW OVERRIDES */
        @media (max-width: 980px) {
          .home-quicklinks { padding-top: 16px; }
          
          .mobile-nav-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
            margin-bottom: 18px;
            padding: 0 8px;
          }
          .grid-nav-btn {
            border-radius: 4px;
            font-size: 11px;
            font-weight: 800;
            text-align: center;
            padding: 10px 2px;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1.25;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 1px 3px rgba(0,0,0,0.08);
            text-decoration: none;
            word-break: break-word;
            background: #ffffff;
            color: #0f172a;
          }
          
          .grid-nav-btn.solid-blue { background: linear-gradient(180deg, #3b82f6, #2563eb); color: #fff; border: 1px solid #1d4ed8; text-shadow: 0 1px 1px rgba(0,0,0,0.2); }
          .grid-nav-btn.solid-orange { background: linear-gradient(180deg, #f97316, #ea580c); color: #fff; border: 1px solid #c2410c; text-shadow: 0 1px 1px rgba(0,0,0,0.2); }
          .grid-nav-btn.solid-dark { background: linear-gradient(180deg, #1e40af, #1e3a8a); color: #fff; border: 1px solid #172554; }
          .grid-nav-btn.outline-blue { background: #f0f9ff; color: #2563eb; border: 1px solid #bfdbfe; font-weight: 700; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
          .grid-nav-btn.outline-dark { background: #fff; color: #0f172a; border: 1px solid #cbd5e1; font-weight: 800; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
          .grid-nav-btn.solid-purple { background: linear-gradient(135deg, #a855f7, #7e22ce); color: #fff; border: 1px solid #6b21a8; text-shadow: 0 1px 1px rgba(0,0,0,0.2); box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 4px 10px rgba(168,85,247,0.2); }
          .grid-nav-btn.outline-purple { background: #faf5ff; color: #7e22ce; border: 1px solid #e9d5ff; font-weight: 800; }
          .grid-nav-btn.outline-orange { background: #fff7ed; color: #ea580c; border: 1px solid #fed7aa; font-weight: 800; }
          .grid-nav-btn.solid-green { background: linear-gradient(135deg, #10b981, #059669); color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 4px 10px rgba(16,185,129,0.25); border: 1px solid #047857; text-shadow: 0 1px 1px rgba(0,0,0,0.2); }

          /* Mobile adjustments for pills */
          .home-links { 
            gap: 8px 6px; 
            padding: 0 6px; 
          }
          .home-link-btn { 
            flex: 1 1 auto; 
            padding: 12px 10px; 
            font-size: 13px; 
            min-width: 28%; 
            white-space: normal;
          }

          .mobile-bottom-search {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 16px 12px;
            margin-top: 24px;
            margin-bottom: 16px;
            border-radius: 8px;
            text-align: left;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
          }
          .mobile-bottom-search h3 {
            font-size: 14px; font-weight: 900; margin: 0 0 10px; color: #0f172a;
          }
          .mbs-row {
            display: flex; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; background: #fff; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
          }
          .mbs-row input {
            flex: 1; height: 42px; border: none; padding: 0 12px; font-size: 13px; outline: none;
          }
          .mbs-row input:focus { border-color: #0ea5e9; }
          .mbs-row button {
            background: linear-gradient(180deg, #3b82f6, #2563eb); color: #fff; border: none; padding: 0 16px; font-weight: 800; font-size: 13px; display: flex; align-items: center; gap: 6px;
          }
        }
      `;
      document.head.appendChild(style);
    }

    let data = null;
    try {
      const r = await fetch("header_links.json", { cache: "no-store" });
      if (r.ok) data = await r.json();
    } catch (_) {}

    let waLink = "https://whatsapp.com/channel/0029VaA2aD4FCCoW3q8y6x25";
    if (data && data.header_links) {
        const waObj = data.header_links.find(l => safe(l.name).toLowerCase().includes("whatsapp"));
        if (waObj && (waObj.url || waObj.link)) waLink = waObj.url || waObj.link;
    }
    
    // ✅ EXACT MOBILE GRID UNTOUCHED, EXCEPT NEW URLS
    if (wrap && !document.getElementById("mobile-nav-grid")) {
        const mobileNavWrap = document.createElement("div");
        mobileNavWrap.id = "mobile-nav-grid";
        mobileNavWrap.className = "mobile-nav-grid";

        const mLinks = [
            { name: "Latest Jobs", url: "https://www.topsarkarijobs.com/view.html?section=latest%20jobs", cls: "solid-blue" },
            { name: "Study wise jobs", url: "category.html?group=study", cls: "outline-blue" },
            { name: "Categories wise jobs", url: "category.html?group=popular", cls: "outline-blue" },
            { name: "State wise Jobs", url: "category.html?group=state", cls: "outline-blue" },
            
            { name: "Admissions", url: "category.html?group=admissions", cls: "outline-purple" },
            { name: "Resume/CV Maker", url: "https://www.topsarkarijobs.com/view.html?url=https%253A%252F%252Fsarkariresulttools.net%252Fresume-maker%252F&name=Resume%2520CV%2520Maker&job=resume-cv-makerume-cv-maker", cls: "outline-purple" },
            { name: "CSC Services <i class='fa-solid fa-chevron-down' style='font-size:9px;margin-left:3px;'></i>", url: "govt-services.html", cls: "outline-purple" },
            { name: "Study Material", url: "category.html?group=study-material", cls: "outline-purple" },
            
            // ✅ Results correctly linked. Admit Card correctly linked.
            { name: "Results", url: "https://www.topsarkarijobs.com/view.html?section=results", cls: "outline-orange" },
            { name: "Admit Card", url: "https://www.topsarkarijobs.com/view.html?section=Admit%20cards%20Exams%20Date", cls: "outline-orange" },
            { name: "Latest Khabar", url: "category.html?group=khabar", cls: "outline-orange" },
            { name: "Join WhatsApp", url: waLink, cls: "solid-green" } 
        ];

        mLinks.forEach(l => {
            const a = document.createElement("a");
            a.className = `grid-nav-btn ${l.cls}`;
            a.href = l.url;
            a.innerHTML = l.name;
            mobileNavWrap.appendChild(a);
        });

        wrap.insertBefore(mobileNavWrap, wrap.firstChild);
    }

    const links = Array.isArray(data?.home_links) ? data.home_links : [];
    if (links.length) {
      
      const excludeList = [
          "latest jobs", "study wise", "categories wise", "popular categories", "state wise",
          "admissions", "admission", "resume", "cv maker", "csc", "study material",
          "results", "result", "admit card", "khabar", "helpdesk", "home", "tools", "whatsapp"
      ];

      const colorMap = { 
        "bg-red-600": "linear-gradient(180deg, #ef4444, #dc2626)", 
        "bg-slate-600": "linear-gradient(180deg, #94a3b8, #64748b)", 
        "bg-amber-600": "linear-gradient(180deg, #f59e0b, #d97706)", 
        "bg-zinc-400": "linear-gradient(180deg, #a1a1aa, #71717a)", 
        "bg-green-600": "linear-gradient(180deg, #10b981, #059669)", 
        "bg-pink-500": "linear-gradient(180deg, #f43f5e, #e11d48)", 
        "bg-yellow-600": "linear-gradient(180deg, #eab308, #ca8a04)", 
        "bg-red-500": "linear-gradient(180deg, #f87171, #ef4444)" 
      };

      const fallbackColors = [
          "linear-gradient(180deg, #ea580c, #9a3412)", 
          "linear-gradient(180deg, #3b82f6, #1e40af)", 
          "linear-gradient(180deg, #be185d, #831843)", 
          "linear-gradient(180deg, #6366f1, #3730a3)", 
          "linear-gradient(180deg, #10b981, #064e3b)", 
          "linear-gradient(180deg, #b45309, #78350f)", 
          "linear-gradient(180deg, #8b5cf6, #5b21b6)", 
          "linear-gradient(180deg, #0ea5e9, #0369a1)"  
      ];

      let validLinks = [];
      links.forEach((l) => {
        let name = safe(l?.name);
        if (name.includes("लाडो लक्ष्मी योजना: पैसा आया है या नहीं आया यहाँ से चेक करें")) {
            name = "लाडो लक्ष्मी योजना: पैसा आया है या नहीं - यहाँ से चेक करें";
        }
        const nLower = name.toLowerCase().trim();
        if (excludeList.some(ex => nLower.includes(ex))) return;
        
        const url = safe(l?.url || l?.link);
        if (!name || !url) return;
        
        validLinks.push({ ...l, name: name, url: url });
      });

      let topHeadlineIndex = validLinks.findIndex(l => l.name.toLowerCase().includes("headlines"));
      let topHeadline = null;
      if (topHeadlineIndex > -1) {
          topHeadline = validLinks.splice(topHeadlineIndex, 1)[0];
      }

      validLinks.sort((a, b) => a.name.length - b.name.length);
      let mixedLinks = [];
      let left = 0; let right = validLinks.length - 1;
      while (left <= right) {
          if (left === right) { mixedLinks.push(validLinks[left]); break; }
          mixedLinks.push(validLinks[right]); 
          mixedLinks.push(validLinks[left]);  
          right--; left++;
      }

      const finalLinks = topHeadline ? [topHeadline, ...mixedLinks] : mixedLinks;

      host.innerHTML = "";
      finalLinks.forEach((l, index) => {
        const a = document.createElement("a");
        a.className = "home-link-btn";
        a.href = normalizeUrl(l.url);
        if (l.external) { a.target = "_blank"; a.rel = "noopener"; }
        
        if (l.name.toLowerCase().includes("headlines")) {
             a.style.background = "linear-gradient(180deg, #ef4444, #991b1b)";
             a.style.width = "100%"; 
        } else {
             a.style.background = colorMap[safe(l.color)] || fallbackColors[index % fallbackColors.length];
        }
        
        const icon = safe(l.icon);
        if (icon) a.innerHTML = `<i class="${icon}"></i><span>${l.name}</span>`;
        else a.textContent = l.name;
        host.appendChild(a);
      });
    }

    if (wrap && !document.getElementById("mobile-bottom-search")) {
        const mbs = document.createElement("div");
        mbs.id = "mobile-bottom-search";
        mbs.className = "mobile-bottom-search";
        mbs.innerHTML = `
            <h3>Search Sarkari नौकरियाँ - Just Click Below</h3>
            <div class="mbs-row">
                <input id="mobileBottomSearchInput" type="search" placeholder="Search job categories, results, admit cards..." autocomplete="off" />
                <button type="button" id="mobileBottomSearchBtn"><i class="fa-solid fa-magnifying-glass"></i> Search</button>
            </div>
            <div id="mobileBottomSearchResults" class="search-results" style="margin-top: 10px; text-align: left;"></div>
        `;
        wrap.appendChild(mbs);
    }
  }

  function removeHomeMainPageCtaLinks() {
    if (!(page === "index.html" || page === "")) return;
    const wrap = document.getElementById("dynamic-sections");
    if (!wrap) return;

    const needles = [
      "╰┈➤🏠Website का Main Home Page खोलने के लिए यहाँ क्लिक करें",
      "Website का Main Home Page खोलने के लिए यहाँ क्लिक करें",
      "Main Home Page खोलने के लिए यहाँ क्लिक करें",
      "Website का Main Home Page",
    ];

    const els = Array.from(wrap.querySelectorAll("a, button"));
    els.forEach((el) => {
      const t = safe(el.textContent).replace(/\s+/g, " ");
      if (!t) return;
      if (needles.some((n) => t.includes(n))) el.remove();
    });
  }

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

    const groupMeta = { study: "Study wise jobs", popular: "Popular job categories", state: "State wise jobs", admissions: "Admissions", "admit-result": "Admit Card / Result", khabar: "Latest Khabar", "study-material": "Study Material & Top Courses" };
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

  async function initToolsPage() {
    if (!isToolsPage) return;

    const categoriesView = $("#categories-view");
    const toolsView = $("#tools-view");
    const toolsGrid = $("#tools-grid");
    const toolsTitle = $("#tools-title span") || $("#tools-title");
    const backBtn = $("#back-button");
    const categoryButtons = $$(".category-button");

    if (!categoriesView || !toolsView || !toolsGrid || !categoryButtons.length) return;

    const fallbackData = {
      image: [
         { name: "Image Resizer", url: "https://imageresizer.com/", icon: "fa-solid fa-compress", external: true },
         { name: "Compress Image", url: "https://tinypng.com/", icon: "fa-solid fa-file-image", external: true },
         { name: "Passport Photo Maker", url: "https://www.cutout.pro/passport-photo-maker", icon: "fa-solid fa-id-card", external: true }
      ],
      pdf: [
         { name: "JPG to PDF", url: "https://www.ilovepdf.com/jpg_to_pdf", icon: "fa-solid fa-file-pdf", external: true },
         { name: "Compress PDF", url: "https://www.ilovepdf.com/compress_pdf", icon: "fa-solid fa-file-zipper", external: true },
         { name: "Merge PDF", url: "https://www.ilovepdf.com/merge_pdf", icon: "fa-solid fa-file-circle-plus", external: true }
      ],
      video: [
         { name: "Video Compressor", url: "https://www.freeconvert.com/video-compressor", icon: "fa-solid fa-video", external: true },
         { name: "MP4 to MP3", url: "https://cloudconvert.com/mp4-to-mp3", icon: "fa-solid fa-music", external: true }
      ]
    };

    let toolsData = fallbackData;
    try {
      const r = await fetch("tools.json", { cache: "no-store" });
      if (r.ok) {
        const json = await r.json();
        if (json && Object.keys(json).length > 0) toolsData = json;
      }
    } catch (_) {}

    const showCategories = () => {
      toolsView.classList.add("hidden");
      categoriesView.classList.remove("hidden");
      if(history.pushState) history.pushState(null, null, location.pathname);
      window.scrollTo({ top: 0, behavior: "instant" });
    };

    const showTools = (categoryKey) => {
      const list = Array.isArray(toolsData[categoryKey]) ? toolsData[categoryKey] : [];
      const titleMap = { image: "Image Tools", pdf: "PDF Tools", video: "Video/Audio Tools" };
      if (toolsTitle) toolsTitle.textContent = titleMap[categoryKey] || "Tools";

      toolsGrid.innerHTML = "";
      if (!list.length) {
        toolsGrid.innerHTML = `<div class="col-span-full p-4 text-center text-gray-600">No tools found.</div>`;
      } else {
        list.forEach((t) => {
          const name = safe(t.name) || "Open Tool";
          const url = t.url || t.link || "";
          if (!url) return;
          const isExternal = t.external === true;
          const a = document.createElement("a");
          a.className = "p-4 rounded-lg bg-white border border-gray-200 hover:bg-blue-50 hover:border-blue-300 transition duration-300 flex items-start gap-3 text-left";
          a.href = isExternal ? normalizeUrl(url) : openInternal(url, name);
          if (isExternal) { a.target = "_blank"; a.rel = "noopener"; }

          const iconClass = safe(t.icon) || "fas fa-wand-magic-sparkles";
          a.innerHTML = `
            <div class="mt-0.5 text-xl text-blue-600"><i class="${iconClass}"></i></div>
            <div><div class="font-semibold text-gray-800">${name}</div><div class="text-sm text-gray-500 mt-1">Open tool</div></div>
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

    const params = new URLSearchParams(location.search);
    const cat = params.get("cat");
    if (cat && toolsData[cat]) {
      showTools(cat);
    } else {
      showCategories();
    }
  }

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
      const name = safe(s.name || s.service).replace("ceck", "check");
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

  async function initGlobalLiveSearch() {
    const inputs = [];
    
    const homeInput = document.getElementById("siteSearchInput");
    if (homeInput) inputs.push({ input: homeInput, resultsId: "searchResults" });
    
    const sectionInput = document.getElementById("sectionSearchInput");
    if (sectionInput) inputs.push({ input: sectionInput, resultsId: "sectionSearchResults" });
    
    const mobileBottomInput = document.getElementById("mobileBottomSearchInput");
    if (mobileBottomInput) inputs.push({ input: mobileBottomInput, resultsId: "mobileBottomSearchResults" });

    if (!inputs.length) return;

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

    inputs.forEach(({ input, resultsId }) => {
      const resultsWrap = document.getElementById(resultsId);
      if (!resultsWrap) return;

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
            let href = normalizeUrl(m.url);
            const isExternal = href.startsWith("http") && !href.includes(location.hostname);
            
            const a = document.createElement("a");
            a.className = "search-result-item";
            a.href = href;
            if (isExternal) {
                a.target = "_blank";
                a.rel = "noopener";
            }
            
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
    });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    buildMobileMenu();
    safeHideOldSearchBars(); 
    
    await injectHeaderFooter();
    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    initFAQ();

    if (page === "index.html" || page === "") {
      await renderHomepageSections();
      removeHomeMainPageCtaLinks();
    }
    
    await renderHomeQuickLinks();
    await initCategoryPage();
    await initToolsPage();
    
    if (page === "govt-services.html") {
      ensureSupabaseClient().catch(() => {});
    }
    initCscModal();
    await renderServicesPage();
    
    await initGlobalLiveSearch();
    
    setTimeout(() => {
        safeHideOldSearchBars();
        initGlobalLiveSearch();
    }, 300); 
  });
})();
