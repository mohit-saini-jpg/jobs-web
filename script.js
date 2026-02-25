(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  const isToolsPage = location.pathname.includes("tools");

  const safe = (v) => (v ?? "").toString().trim();

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
             <a href="helpdesk.html" class="mhb-btn">Helpdesk <i class="fa-solid fa-chevron-down"></i></a>
             <a href="index.html" class="mhb-btn">Home <i class="fa-solid fa-chevron-down"></i></a>
          </div>
          <a href="tools.html" class="mhb-btn mhb-full">Tools</a>
        `;
        headerRow.insertBefore(btns, headerActions);
    }
  }

  // ✅ LASER-TARGETED HIDER: Safely hides old search elements without touching Jobs!
  function safeHideOldSearchBars() {
    if (window.innerWidth <= 980) {
        const oldInputs = document.querySelectorAll('#siteSearchInput, #sectionSearchInput, .search-row');
        oldInputs.forEach(el => {
            if (!el.closest('#mobile-bottom-search')) {
                el.style.setProperty('display', 'none', 'important');
                
                const parentBox = el.closest('.search-card') || el.closest('.top-search') || el.parentElement;
                if (parentBox && parentBox.id !== 'mobile-bottom-search' && parentBox.id !== 'main') {
                    // Only hide if it does NOT contain the main job lists or tables
                    if (!parentBox.querySelector('table, .section-list, article')) {
                        parentBox.style.setProperty('display', 'none', 'important');
                    }
                }
            }
        });

        // Hide floating text strictly related to old search
        document.querySelectorAll('h1, h2, h3, p, span, div').forEach(el => {
            if (el.children.length === 0 || el.tagName === 'H2' || el.tagName === 'P') {
                const txt = (el.textContent || "").trim();
                if (txt === "Search across Top Sarkari Jobs" || txt === "Search jobs, results, admit cards, categories, CSC services and tools.") {
                    el.style.setProperty('display', 'none', 'important');
                    if (el.parentElement && el.parentElement.tagName === 'DIV' && el.parentElement.id !== 'main') {
                        if (!el.parentElement.querySelector('table, .section-list, article')) {
                            el.parentElement.style.setProperty('display', 'none', 'important');
                        }
                    }
                }
            }
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

  // ✅ PERFECTED PREMIUM MOBILE APP GRID & PILLS
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

    if (!document.getElementById("home-quicklinks-style")) {
      const style = document.createElement("style");
      style.id = "home-quicklinks-style";
      style.textContent = `
        .home-quicklinks { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 0; }
        
        /* DESKTOP VIEW */
        @media (min-width: 981px) {
          .home-quicklinks { padding: 0 0 24px; }
          .desktop-hidden { display: none !important; }
          .mobile-nav-grid, .mobile-bottom-search { display: none !important; }
        }

        .home-links { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: center; }
        
        .home-link-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 8px 16px;
          border-radius: 99px;
          color: #fff;
          font-weight: 700;
          font-size: 14px;
          text-decoration: none;
          line-height: 1.2;
          box-shadow: 0 4px 10px rgba(0,0,0,0.08);
          border: 1px solid rgba(255,255,255,0.2);
          white-space: nowrap;
          transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
        }
        .home-link-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 15px rgba(0,0,0,0.15);
          filter: brightness(1.05);
        }
        .home-link-btn:active { transform: translateY(0); }
        
        /* MOBILE VIEW OVERRIDES - PREMIUM UI */
        @media (max-width: 980px) {
          .home-quicklinks { padding-top: 16px; }
          
          /* The Premium 4-Column Rectangular App Grid */
          .mobile-nav-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            grid-auto-rows: 1fr;
            gap: 8px;
            margin-bottom: 24px;
            background: #ffffff;
            padding: 12px;
            border-radius: 16px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            border: 1px solid rgba(0,0,0,0.04);
          }
          .grid-nav-btn {
            border-radius: 8px;
            font-size: 11px;
            font-weight: 800;
            text-align: center;
            padding: 10px 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1.3;
            text-decoration: none;
            word-break: break-word;
            height: 100%;
            transition: transform 0.2s;
            letter-spacing: -0.2px;
          }
          .grid-nav-btn:active { transform: scale(0.96); }
          
          /* Glossy Premium App Themes */
          .grid-nav-btn.solid-blue { background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 4px 10px rgba(37,99,235,0.25); border: 1px solid #1e40af; text-shadow: 0 1px 1px rgba(0,0,0,0.2); }
          .grid-nav-btn.solid-orange { background: linear-gradient(135deg, #f97316, #ea580c); color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 4px 10px rgba(234,88,12,0.25); border: 1px solid #c2410c; text-shadow: 0 1px 1px rgba(0,0,0,0.2); }
          .grid-nav-btn.solid-dark { background: linear-gradient(135deg, #1e40af, #1e3a8a); color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,0.1), 0 4px 10px rgba(30,58,138,0.25); border: 1px solid #172554; }
          .grid-nav-btn.outline-blue { background: linear-gradient(180deg, #ffffff, #f0f9ff); color: #1d4ed8; border: 1px solid #bfdbfe; font-weight: 800; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }
          .grid-nav-btn.outline-dark { background: linear-gradient(180deg, #ffffff, #f8fafc); color: #334155; border: 1px solid #cbd5e1; font-weight: 800; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }

          /* Perfectly Packed Pill Boxes */
          .home-links { 
            display: flex;
            flex-wrap: wrap;
            gap: 8px; 
            justify-content: center; 
            align-content: center;
            padding: 0 6px; 
            margin-bottom: 0px; 
          }
          .home-link-btn { 
            flex: 1 1 auto; 
            padding: 10px 12px; 
            font-size: 13px; 
            text-align: center;
            justify-content: center;
            margin: 0;
            min-width: calc(30% - 8px); 
            border-radius: 12px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.08);
            border: 1px solid rgba(255,255,255,0.15);
            letter-spacing: 0.2px;
          }
          
          /* Beautiful Custom Bottom Search exactly like screenshot */
          .mobile-bottom-search {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 20px 14px;
            margin-top: 28px;
            margin-bottom: 16px;
            border-radius: 16px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.06);
          }
          .mobile-bottom-search h3 {
            font-size: 15px;
            font-weight: 900;
            margin: 0 0 14px;
            color: #0f172a;
            letter-spacing: -0.2px;
          }
          .mbs-row {
            display: flex;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            overflow: hidden;
            background: #f8fafc;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
          }
          .mbs-row input {
            flex: 1;
            height: 46px;
            border: none;
            background: transparent;
            padding: 0 14px;
            font-size: 14px;
            outline: none;
            color: #0f172a;
          }
          .mbs-row input:focus { background: #fff; border-color: #0ea5e9; }
          .mbs-row button {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: #fff;
            border: none;
            padding: 0 20px;
            font-weight: 800;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
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
    
    // ✅ INJECT PREMIUM 4x3 APP GRID
    if (wrap && !document.getElementById("mobile-nav-grid")) {
        const mobileNavWrap = document.createElement("div");
        mobileNavWrap.id = "mobile-nav-grid";
        mobileNavWrap.className = "mobile-nav-grid";

        // ✅ EXACT ABSOLUTE LINK FOR LATEST JOBS (Fixed logic)
        const mLinks = [
            { name: "Latest Jobs", url: "https://www.topsarkarijobs.com/view.html?section=latest%20jobs", cls: "solid-blue" },
            { name: "Study wise jobs", url: "category.html?group=study", cls: "outline-blue" },
            { name: "Categories wise jobs", url: "category.html?group=popular", cls: "outline-blue" },
            { name: "State wise Jobs", url: "category.html?group=state", cls: "outline-blue" },
            
            { name: "Admissions", url: "category.html?group=admissions", cls: "outline-blue" },
            { name: "Resume/CV Maker", url: "tools.html", cls: "solid-dark" },
            { name: "CSC Services <i class='fa-solid fa-chevron-down' style='font-size:9px;margin-left:3px;'></i>", url: "govt-services.html", cls: "solid-dark" },
            { name: "Study Material", url: "category.html?group=study-material", cls: "outline-dark" },
            
            { name: "Results", url: "result.html", cls: "solid-orange" },
            { name: "Admit Card", url: "category.html?group=admit-result", cls: "solid-orange" },
            { name: "Latest Khabar", url: "category.html?group=khabar", cls: "outline-blue" },
            { name: "Join WhatsApp", url: waLink, cls: "solid-dark" } 
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

    // Process bottom pill links
    const links = Array.isArray(data?.home_links) ? data.home_links : [];
    if (links.length) {
      
      const excludeList = [
          "latest jobs", "study wise", "categories wise", "popular categories", "state wise",
          "admissions", "admission", "resume", "cv maker", "csc", "study material",
          "results", "result", "admit card", "khabar", "helpdesk", "home", "tools", "whatsapp"
      ];

      // Beautiful Vibrant Pill Gradients
      const colorMap = { 
        "bg-red-600": "linear-gradient(135deg, #ef4444, #dc2626)", 
        "bg-slate-600": "linear-gradient(135deg, #64748b, #475569)", 
        "bg-amber-600": "linear-gradient(135deg, #f59e0b, #ea580c)", 
        "bg-zinc-400": "linear-gradient(135deg, #a1a1aa, #71717a)", 
        "bg-green-600": "linear-gradient(135deg, #10b981, #059669)", 
        "bg-pink-500": "linear-gradient(135deg, #f43f5e, #e11d48)", 
        "bg-yellow-600": "linear-gradient(135deg, #eab308, #ca8a04)", 
        "bg-red-500": "linear-gradient(135deg, #f87171, #ef4444)" 
      };

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

      // 1. Extract Top Headlines so it's always forced to the #1 top position
      let topHeadlineIndex = validLinks.findIndex(l => l.name.toLowerCase().includes("headlines"));
      let topHeadline = null;
      if (topHeadlineIndex > -1) {
          topHeadline = validLinks.splice(topHeadlineIndex, 1)[0];
      }

      // 2. Mix lengths so flexbox fills edges perfectly like bricks
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
      finalLinks.forEach((l) => {
        const a = document.createElement("a");
        a.className = "home-link-btn";
        a.href = normalizeUrl(l.url);
        if (l.external) { a.target = "_blank"; a.rel = "noopener"; }
        
        a.style.background = colorMap[safe(l.color)] || "linear-gradient(135deg, #64748b, #475569)";
        
        const icon = safe(l.icon);
        if (icon) a.innerHTML = `<i class="${icon}"></i><span>${l.name}</span>`;
        else a.textContent = l.name;
        host.appendChild(a);
      });
    }

    // ✅ INJECT PERFECT BOTTOM SEARCH BAR
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
            <div id="mobileBottomSearchResults" class="search-results" style="margin-top: 12px; text-align: left;"></div>
        `;
        wrap.appendChild(mbs);
    }
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

    // Filter Garbage
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

    const mainContainer = $("#main") || $("main") || document.body;
    let seoBox = document.getElementById("dynamic-seo-box");
    if (seoBox) seoBox.remove(); 

    let seoHTML = "";

    if (group === "study") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Government Exam Study Resources 2026 – Free Study Material, Syllabus, Mock Tests & Preparation Strategy</h2>
          <p>Preparing for a Sarkari Job in India requires more than just hard work — it requires the right strategy, authentic study material, structured revision plan, and consistent practice. The Study section of Top Sarkari Jobs is designed to be your complete preparation hub for all major Government Exams 2026 including UPSC, SSC, Railway, Banking, State PSC, Police, Defence, CUET, JEE, NEET and other competitive exams.</p>
          <p>Yahan par aapko milega free study material, official syllabus guidance, trusted government learning portals, previous year question papers, conceptual video lectures, and structured preparation roadmap — sab ek hi jagah par. This page is not just about downloading PDFs. It is about building strong conceptual clarity, analytical ability and exam confidence.</p>
          
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Why Structured Study Resources Matter</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">Government exams in India are highly competitive. Lakhs of candidates apply every year for limited vacancies. Random preparation se selection mushkil hota hai. Structured preparation se success possible hoti hai. Most exams test:</p>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>Conceptual clarity & Analytical reasoning</li>
                <li>Current affairs awareness</li>
                <li>Time management & Accuracy under pressure</li>
              </ul>
            </div>
            <div class="seo-card">
              <h3>Start with NCERT – Foundation</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">Almost every major competitive exam is linked to NCERT concepts (History, Geography, Polity, Economics, General Science). For UPSC and State PSC, Class 6–12 is mandatory.</p>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in/textbook.php</a></p>
            </div>
            <div class="seo-card">
              <h3>SWAYAM & NPTEL – Online Courses</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">SWAYAM offers free courses by IIT/IIM professors for Gen Studies, Economics, etc.</p>
              <p style="font-size: 13px; margin-bottom: 8px; font-weight: 600;">👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">NPTEL offers technical & analytical lectures (Aptitude, Reasoning, Engineering).</p>
              <p style="font-size: 13px; font-weight: 600;">👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nptel.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>National Digital Library (NDLI)</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">Access academic books, research material, and previous year papers.</p>
              <p style="font-size: 13px; margin-bottom: 8px; font-weight: 600;">👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ndl.iitkgp.ac.in</a></p>
            </div>
          </div>
          <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line);">
            <h3 style="font-size: 16px; font-weight: 900; margin-bottom: 8px;">Smart Study Plan & Syllabus Strategy</h3>
            <p style="font-size: 14px; color: var(--muted); line-height: 1.6; margin-bottom: 8px;">Always download the official syllabus (e.g., from <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">upsc.gov.in</a> or <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a>). Avoid studying from too many sources, ignoring past papers, and following unverified PDFs.</p>
            <ul style="list-style-type: decimal; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 14px;">
              <li>Complete NCERT (Foundation)</li>
              <li>Download official syllabus & create timetable</li>
              <li>Take SWAYAM/NPTEL lectures</li>
              <li>Solve previous year question papers & weekly mock tests</li>
            </ul>
            <p style="font-size: 14px; font-weight: 700; color: #0ea5e9; margin-top: 10px;">Preparation smart honi chahiye, sirf hard work se selection nahi hota.</p>
          </div>
        </section>`;
    } else if (group === "popular") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Popular Government Exams 2026 – Most Applied Sarkari Jobs in India</h2>
          <p>Every year, millions of aspirants apply for popular government exams in India. These exams offer job security, stable salary, pension benefits, and long-term career growth. The Popular section of Top Sarkari Jobs highlights the most searched, most competitive and high-demand Sarkari exams in India for 2026.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>UPSC Civil Services Examination</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">Recruits for IAS, IPS, IFS and other Group A services. Prep: NCERT foundation, daily newspaper, analytical writing, mock tests.</p>
              <p style="font-size: 13px; margin-bottom: 4px; font-weight: 600;">Official: 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">upsc.gov.in</a></p>
            </div>
            <div class="seo-card">
              <h3>NTA Conducted Exams</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">NTA conducts CUET (UG), JEE Main, NEET UG, UGC NET, CSIR NET.</p>
              <p style="font-size: 13px; margin-bottom: 4px; font-weight: 600;">Official: 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>SSC & Railway Exams</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">SSC (CGL, CHSL, MTS) and RRB (NTPC, Group D, ALP) require quantitative aptitude, english, general awareness, speed & accuracy.</p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NCERT Books:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in/textbook.php</a></p>
            </div>
            <div class="seo-card">
              <h3>Banking Exams (IBPS / SBI / RBI)</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">Popular for urban postings and structured promotions. Requires strong quantitative aptitude and reasoning.</p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>Concept lectures:</strong> 👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nptel.ac.in</a></p>
            </div>
          </div>
        </section>`;
    } else if (group === "state") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>State Wise Sarkari Jobs 2026 – State PSC, Police & Local Recruitment Updates</h2>
          <p>India has 28 states and each state conducts its own recruitment for administrative, police, teaching and technical posts. This section helps candidates explore State PSC Notifications, State Police Recruitment, State Teaching Jobs, and State Level Group B & C Vacancies.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Why State Jobs Are Important</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>Local posting & Language advantage</li>
                <li>Stable career & Regional growth</li>
              </ul>
            </div>
            <div class="seo-card">
              <h3>Official Government Portals</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>Civil Services:</strong> 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">upsc.gov.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>National Exams:</strong> 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a></p>
              <p style="font-size: 13px; color: var(--muted);">Always verify notifications from official sources.</p>
            </div>
            <div class="seo-card">
              <h3>State Exam Preparation Strategy</h3>
              <p style="font-size: 13px; margin-bottom: 4px;">1. NCERT foundation: 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;">2. State specific history: 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ndl.iitkgp.ac.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;">3. Concept lectures: 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
            </div>
            <div class="seo-card">
              <h3>Subjects Common in State Exams</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>State History & Geography</li>
                <li>Indian Polity & Current Affairs</li>
              </ul>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">Preparation must combine local + national knowledge.</p>
            </div>
          </div>
        </section>`;
    } else if (group === "admissions") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>University Admissions 2026 – Entrance Exams, Eligibility & Preparation Resources</h2>
          <p>This section covers national and university-level entrance examinations. Students searching for CUET 2026, JEE Main 2026, NEET UG 2026, UGC NET, or Central University Admissions will find verified and structured guidance here.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>National Testing Agency (NTA)</h3>
              <p style="font-size: 13px; color: var(--muted); margin-bottom: 8px;">NTA conducts major national entrance exams. Candidates must track deadlines, download admit cards, and review correction notices.</p>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>Academic Preparation Resources</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NCERT:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in/textbook.php</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>SWAYAM:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NPTEL:</strong> 👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nptel.ac.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NDLI:</strong> 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ndl.iitkgp.ac.in</a></p>
            </div>
          </div>
          <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line);">
            <h3 style="font-size: 16px; font-weight: 900; margin-bottom: 8px;">Admission Preparation Strategy</h3>
            <p style="font-size: 14px; color: var(--muted);">Follow official syllabus, practice mock tests, revise fundamentals, and track official announcements. Avoid relying on unverified portals.</p>
          </div>
        </section>`;
    } else if (group === "admit-result") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Sarkari Admit Card & Result 2026 – Official Download Links & Verification Guide</h2>
          <p>This section provides verified links for Sarkari Result 2026, Government Exam Admit Cards, Scorecards, and Merit Lists.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Official Portals</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NTA:</strong> 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>UPSC:</strong> 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">upsc.gov.in</a></p>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">Always use official websites only.</p>
            </div>
            <div class="seo-card">
              <h3>Between Admit Card & Exam</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NCERT:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in/textbook.php</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>Concept courses:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>Advanced practice:</strong> 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ndl.iitkgp.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>After Result Declaration</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>Check cut-off</li>
                <li>Download scorecard</li>
                <li>Prepare for next stage</li>
              </ul>
            </div>
          </div>
        </section>`;
    } else if (group === "khabar") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Latest Government Exam News 2026 – Official Notifications & Updates</h2>
          <p>Stay updated with exam date changes, application extensions, correction windows, and result announcements.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Trusted Sources</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NTA Official:</strong> 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nta.ac.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>UPSC Official:</strong> 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">upsc.gov.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>Educational portal:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
            </div>
            <div class="seo-card">
              <h3>Why News Section Matters</h3>
              <p style="font-size: 13px; color: var(--muted);">Timely information helps avoid missed deadlines. Never rely on rumors.</p>
            </div>
          </div>
        </section>`;
    } else if (group === "study-material") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Free Study Material for Government Exams – Download PDFs & Online Courses</h2>
          <p>This page is dedicated exclusively to preparation material.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Foundation & Online Learning</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NCERT Textbooks:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ncert.nic.in/textbook.php</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>SWAYAM:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">swayam.gov.in</a></p>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>NPTEL:</strong> 👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">nptel.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>Research & Reference Library</h3>
              <p style="font-size: 13px; margin-bottom: 4px;"><strong>National Digital Library:</strong> 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">ndl.iitkgp.ac.in</a></p>
            </div>
            <div class="seo-card">
              <h3>Complete Preparation Ecosystem</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>Learn basics from NCERT</li>
                <li>Deepen understanding via SWAYAM</li>
                <li>Improve analytical skills through NPTEL</li>
                <li>Practice using NDLI materials</li>
                <li>Track official updates via <a href="https://nta.ac.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">NTA</a> & <a href="https://upsc.gov.in" target="_blank" rel="noopener" style="color: #2563eb; text-decoration: underline;">UPSC</a></li>
              </ul>
            </div>
          </div>
        </section>`;
    }

    if (seoHTML) {
      seoBox = document.createElement("div");
      seoBox.id = "dynamic-seo-box";
      seoBox.innerHTML = seoHTML;
      mainContainer.appendChild(seoBox);
    }
  }

  // Tools Page
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

  // CSC Services 
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

  // ✅ GLOBAL LIVE SEARCH ENGINE (Works for Mobile Bottom Search too)
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
    safeHideOldSearchBars(); // Fire aggressively on load
    
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
    
    // Final aggressive cleanup of old search elements just in case they loaded late
    setTimeout(() => {
        safeHideOldSearchBars();
        initGlobalLiveSearch();
    }, 300); 
  });
})();
