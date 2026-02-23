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
    if (s.startsWith("/") || s.endsWith(".html") || s.startsWith("./") || s.startsWith("../")) return s;
    return "https://" + s.replace(/^\/+/, "");
  }

  // ✅ GARBAGE LINK FILTER
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

  // Homepage Sections
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
    if (!(page === "index.html" || page === "")) return;
    const searchInput = $("#siteSearchInput");
    let host = $("#home-links");
    
    if (!host) {
      const wrap = document.createElement("section");
      wrap.className = "home-quicklinks";
      host = document.createElement("div");
      host.id = "home-links";
      host.className = "home-links";
      wrap.appendChild(host);
      const target = (searchInput && searchInput.closest(".container")) || $("main") || document.body;
      target.parentNode.insertBefore(wrap, target);
    }

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

    const colorMap = { "bg-red-600": "#dc2626", "bg-slate-600": "#475569", "bg-amber-600": "#0ea5a4", "bg-zinc-400": "#9ca3af", "bg-green-600": "#16a34a", "bg-pink-500": "#ec4899", "bg-yellow-600": "#ca8a04", "bg-red-500": "#ef4444" };

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

  // Category Pages (WITH SEO CONTENT INJECTIONS)
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

    // ✅ INJECT SEO CONTENT DYNAMICALLY FOR ALL PAGES
    const mainContainer = $("#main") || $("main") || document.body;
    let seoBox = document.getElementById("dynamic-seo-box");
    if (seoBox) seoBox.remove(); 

    let seoHTML = "";

    if (group === "study") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Government Exam Study Resources 2026 – Free Study Material, Syllabus & Preparation Strategy</h2>
          <p>Welcome to the Study section of Top Sarkari Jobs, your dedicated hub for Government Exam Preparation, Free Study Material, Syllabus Guides, Previous Year Question Papers, Mock Tests and Concept Clarity Resources for all major competitive exams in India.</p>
          <p>Government exams like UPSC, SSC, Railway, Banking, State PSC, Police, Defence and CUET require structured preparation. Random PDFs se selection nahi hota — strategic preparation hoti hai. Yahan par hum aapko verified, official aur high-quality resources provide karte hain jo real exam pattern ke according relevant hain.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Build Strong Foundation with NCERT Books</h3>
              <p style="font-size: 13px; margin-bottom: 8px; color: var(--muted);">Most competitive exams test conceptual understanding from basic subjects:</p>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6;">
                <li>Indian History & Geography</li>
                <li>Polity & Economics</li>
                <li>General Science & Mathematics</li>
              </ul>
              <p style="font-size: 13px; margin-top: 10px; color: var(--muted);">For this reason, NCERT textbooks are considered the backbone of Sarkari exam preparation.</p>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ncert.nic.in/textbook.php</a></p>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">These books (Class 6–12 especially) are essential for UPSC, State PSC, SSC, Railway, and Teaching Exams. Hindi aur English dono versions available hain.</p>
            </div>
            <div class="seo-card">
              <h3>Advanced Concept Learning – SWAYAM</h3>
              <p style="font-size: 13px; margin-bottom: 8px; color: var(--muted);">Government of India initiative offering free online courses in:</p>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6;">
                <li>General Studies & Humanities</li>
                <li>Engineering & Management</li>
                <li>Law & Mathematics</li>
              </ul>
              <p style="font-size: 13px; margin-top: 10px; color: var(--muted);">Once basics are clear, next step is depth.</p>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">swayam.gov.in</a></p>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">These courses are taught by IIT, IIM and central university professors.</p>
            </div>
            <div class="seo-card">
              <h3>NPTEL Courses (IIT Lectures)</h3>
              <p style="font-size: 13px; margin-bottom: 8px; color: var(--muted);">Ideal for technical and analytical preparation:</p>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6;">
                <li>Quantitative Aptitude & Data Interpretation</li>
                <li>Logical Reasoning</li>
                <li>Computer Science & Technical Govt Exams</li>
              </ul>
              <p style="font-size: 13px; margin-top: 10px; font-weight: 600;">👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">nptel.ac.in</a></p>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">These courses improve conceptual strength and analytical thinking.</p>
            </div>
            <div class="seo-card">
              <h3>National Digital Library (NDLI)</h3>
              <p style="font-size: 13px; margin-bottom: 8px; color: var(--muted);">Research & Previous Year Papers provided by IIT Kharagpur:</p>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6;">
                <li>Previous year question papers</li>
                <li>Competitive exam books</li>
                <li>Academic references, Journals & Research papers</li>
              </ul>
              <p style="font-size: 13px; margin-top: 10px; font-weight: 600;">👉 <a href="https://ndl.iitkgp.ac.in/" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ndl.iitkgp.ac.in</a></p>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">Serious aspirants must use NDLI for structured preparation.</p>
            </div>
          </div>
          <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line);">
            <h3 style="font-size: 16px; font-weight: 900; margin-bottom: 8px;">Smart Study Plan for 2026 Exams</h3>
            <ul style="list-style-type: decimal; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 14px;">
              <li>Complete NCERT (6–12)</li>
              <li>Download official syllabus</li>
              <li>Take SWAYAM/NPTEL courses</li>
              <li>Practice previous year papers</li>
              <li>Weekly mock tests & Monthly revision</li>
            </ul>
            <p style="font-size: 14px; font-weight: 700; color: #0ea5e9; margin-top: 10px;">Consistency beats intensity.</p>
          </div>
        </section>`;
    } else if (group === "popular") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Popular Government Exams 2026 – Most Applied Sarkari Jobs in India</h2>
          <p>This section highlights high-demand, high-competition government exams in India. Har saal lakhon candidates apply karte hain for: UPSC Civil Services, SSC CGL / CHSL, Railway RRB NTPC, Banking PO & Clerk, CUET (UG), NEET / JEE, and State PSC.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>UPSC Civil Services</h3>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">upsc.gov.in</a></p>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">UPSC is India’s most prestigious exam. Preparation Strategy: NCERT foundation (6–12), Daily current affairs, SWAYAM lectures for optional subjects, NDLI for research.</p>
            </div>
            <div class="seo-card">
              <h3>NTA Conducted Exams</h3>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">nta.ac.in</a></p>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">NTA conducts CUET, JEE Main, NEET UG, and UGC NET. Candidates must check official portal for Application dates, Admit cards, Results, and Correction windows.</p>
            </div>
            <div class="seo-card">
              <h3>SSC & Railway Exams</h3>
              <ul style="list-style-type: none; margin-left: 0; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li><strong>NCERT Books:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ncert.nic.in/textbook.php</a></li>
                <li><strong>Concept courses:</strong> 👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">nptel.ac.in</a></li>
                <li><strong>Practice material:</strong> 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ndl.iitkgp.ac.in</a></li>
              </ul>
            </div>
          </div>
        </section>`;
    } else if (group === "state") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>State Wise Sarkari Jobs 2026 – Preparation & Official Resources</h2>
          <p>India ke har state ka apna recruitment system hota hai. This section covers state-level job notifications and preparation guidance.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Official State & Central Websites</h3>
              <ul style="list-style-type: none; margin-left: 0; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li><strong>UPSC Portal:</strong> 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">upsc.gov.in</a></li>
                <li><strong>NTA Portal:</strong> 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">nta.ac.in</a></li>
              </ul>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">Always verify notifications from official portals.</p>
            </div>
            <div class="seo-card">
              <h3>State PSC Preparation Strategy</h3>
              <ul style="list-style-type: none; margin-left: 0; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li><strong>NCERT Books:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ncert.nic.in/textbook.php</a></li>
                <li><strong>State specific history & geography:</strong> 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ndl.iitkgp.ac.in</a></li>
                <li><strong>Advanced lectures:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">swayam.gov.in</a></li>
              </ul>
            </div>
            <div class="seo-card">
              <h3>Key Focus Areas for State Exams</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>State history & Local geography</li>
                <li>Current affairs & General Studies</li>
              </ul>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">Structured preparation increases success rate.</p>
            </div>
          </div>
        </section>`;
    } else if (group === "admissions") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>University Admissions & Entrance Exams 2026 – Official Preparation Resources</h2>
          <p>This section covers national entrance exams for undergraduate and postgraduate admissions.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>National Testing Agency (NTA)</h3>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">nta.ac.in</a></p>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">NTA conducts CUET, JEE Main, NEET, and UGC NET. Always check official website for updates.</p>
            </div>
            <div class="seo-card">
              <h3>Entrance Exam Preparation Resources</h3>
              <ul style="list-style-type: none; margin-left: 0; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li><strong>NCERT Books:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ncert.nic.in/textbook.php</a></li>
                <li><strong>SWAYAM Courses:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">swayam.gov.in</a></li>
                <li><strong>NPTEL Lectures:</strong> 👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">nptel.ac.in</a></li>
                <li><strong>NDLI Resources:</strong> 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ndl.iitkgp.ac.in</a></li>
              </ul>
            </div>
            <div class="seo-card">
              <h3>Smart Admission Preparation Tips</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>Focus on syllabus</li>
                <li>Practice mock tests</li>
                <li>Track official announcements</li>
                <li>Avoid unofficial rumors</li>
              </ul>
            </div>
          </div>
        </section>`;
    } else if (group === "admit-result") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Sarkari Admit Card & Result 2026 – Official Download Links</h2>
          <p>This section helps candidates find verified admit cards and results.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Official Result Portals</h3>
              <ul style="list-style-type: none; margin-left: 0; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li><strong>NTA:</strong> 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">nta.ac.in</a></li>
                <li><strong>UPSC:</strong> 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">upsc.gov.in</a></li>
              </ul>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">Never download admit cards from unknown websites.</p>
            </div>
            <div class="seo-card">
              <h3>Before Downloading Admit Card</h3>
              <ul style="list-style-type: disc; margin-left: 18px; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li>Verify registration number</li>
                <li>Check exam center</li>
                <li>Read instructions</li>
                <li>Keep printed copy</li>
              </ul>
            </div>
            <div class="seo-card">
              <h3>Preparation Between Admit Card & Exam</h3>
              <ul style="list-style-type: none; margin-left: 0; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li><strong>NCERT:</strong> 👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ncert.nic.in/textbook.php</a></li>
                <li><strong>Mock practice:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">swayam.gov.in</a></li>
                <li><strong>Revision material:</strong> 👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ndl.iitkgp.ac.in</a></li>
              </ul>
            </div>
          </div>
        </section>`;
    } else if (group === "khabar") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Latest Government Exam News & Updates 2026</h2>
          <p>Stay updated with official exam announcements.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Trusted Sources for News</h3>
              <ul style="list-style-type: none; margin-left: 0; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li><strong>NTA:</strong> 👉 <a href="https://nta.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">nta.ac.in</a></li>
                <li><strong>UPSC:</strong> 👉 <a href="https://upsc.gov.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">upsc.gov.in</a></li>
                <li><strong>Educational courses:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">swayam.gov.in</a></li>
              </ul>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">Always cross-check news from official portals.</p>
            </div>
            <div class="seo-card">
              <h3>Why Official News Matters</h3>
              <p style="font-size: 13px; margin-top: 8px; color: var(--muted);">Avoid misinformation. Government exam timelines change frequently.</p>
            </div>
          </div>
        </section>`;
    } else if (group === "study-material") {
      seoHTML = `
        <section class="seo-block" aria-label="Guides" style="margin-top: 24px;">
          <h2>Free Study Material for Government Exams – Download PDFs & Online Courses</h2>
          <p>This page is dedicated to preparation material.</p>
          <div class="seo-grid">
            <div class="seo-card">
              <h3>Foundation Material</h3>
              <p style="font-size: 13px; margin-bottom: 8px; color: var(--muted);">NCERT Free PDF:</p>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://ncert.nic.in/textbook.php" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ncert.nic.in/textbook.php</a></p>
            </div>
            <div class="seo-card">
              <h3>Advanced Learning</h3>
              <ul style="list-style-type: none; margin-left: 0; color: var(--muted); line-height: 1.6; font-size: 13px;">
                <li><strong>SWAYAM:</strong> 👉 <a href="https://swayam.gov.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">swayam.gov.in</a></li>
                <li><strong>NPTEL:</strong> 👉 <a href="https://nptel.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">nptel.ac.in</a></li>
              </ul>
            </div>
            <div class="seo-card">
              <h3>Research & Question Papers</h3>
              <p style="font-size: 13px; margin-bottom: 8px; color: var(--muted);">NDLI:</p>
              <p style="font-size: 13px; margin-top: 8px; font-weight: 600;">👉 <a href="https://ndl.iitkgp.ac.in" target="_blank" rel="noopener" class="text-sky-600 hover:underline">ndl.iitkgp.ac.in</a></p>
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

    // FALLBACK DATA
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

  // ✅ GLOBAL LIVE SEARCH
  async function initGlobalLiveSearch() {
    const inputs = [];
    const homeInput = document.getElementById("siteSearchInput");
    const sectionInput = document.getElementById("sectionSearchInput");
    
    if (homeInput) inputs.push({ input: homeInput, resultsId: "searchResults" });
    if (sectionInput) inputs.push({ input: sectionInput, resultsId: "sectionSearchResults" });

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
      removeHomeMainPageCtaLinks();
    }
    
    await initCategoryPage();
    await initToolsPage();
    
    // CSC Services Boot Check
    if (page === "govt-services.html") {
      ensureSupabaseClient().catch(() => {});
    }
    initCscModal();
    await renderServicesPage();
    
    // Initialize Search everywhere
    await initGlobalLiveSearch();
  });
})();
