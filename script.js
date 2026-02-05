(() => {
  "use strict";

  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const safe = (v) => (v ?? "").toString().trim();
  const escRE = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  const isHomePageCta = (name, url) => {
    const n = safe(name).toLowerCase();
    const u = safe(url).toLowerCase();
    // Remove the repeated "Main Home Page" button/link that appears in many sections
    return (
      n.includes("website का main home page") ||
      n.includes("main home page") ||
      (n.includes("🏠") && n.includes("home page")) ||
      n.includes("╰┈➤") ||
      (u.includes("topsarkarijobs.com") && (n.includes("home page") || n.includes("main home")))
    );
  };

  // ---- URL normalization (Fix: links not opening when url missing scheme) ----
  function normalizeUrl(raw) {
    const url = safe(raw);
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    if (url.startsWith("//")) return "https:" + url;
    if (url.startsWith("www.")) return "https://" + url;
    // If it's a relative URL like "page.html" keep it as is.
    return url;
  }

  // -------------------------
  // Header/footer links (from header_links.json)
  // -------------------------
  async function loadHeaderLinks(){
    let data = null;

    try{
      const res = await fetch("header_links.json", { cache: "no-store" });
      if(!res.ok) throw new Error("header_links.json not found");
      data = await res.json();
    }catch(err){
      // Fail silently (site should still work even without JSON)
      data = null;
    }

    if(!data) return;

    // Desktop CTA links
    const ctaWrap = $(".header-cta");
    if(ctaWrap && Array.isArray(data.ctas)){
      ctaWrap.innerHTML = "";
      data.ctas.forEach(item=>{
        const a = document.createElement("a");
        a.className = "nav-link";
        a.href = normalizeUrl(item.url) || "#";
        a.textContent = safe(item.name) || "Link";
        a.rel = "noopener";
        ctaWrap.appendChild(a);
      });
    }

    // Footer quick links
    const footerLinks = $(".footer-links");
    if(footerLinks && Array.isArray(data.footerLinks)){
      footerLinks.innerHTML = "";
      data.footerLinks.forEach(item=>{
        const a = document.createElement("a");
        a.href = normalizeUrl(item.url) || "#";
        a.textContent = safe(item.name) || "Link";
        a.rel = "noopener";
        footerLinks.appendChild(a);
      });
    }
  }

  // -------------------------
  // Offcanvas menu (mobile)
  // -------------------------
  function initOffcanvas(){
    const openBtn = $("#openMenu");
    const closeBtn = $("#closeMenu");
    const drawer = $("#mobileDrawer");
    const overlay = $("#drawerOverlay");

    if(!openBtn || !closeBtn || !drawer || !overlay) return;

    const open = () => {
      drawer.hidden = false;
      overlay.hidden = false;
      document.body.style.overflow = "hidden";
    };

    const close = () => {
      drawer.hidden = true;
      overlay.hidden = true;
      document.body.style.overflow = "";
    };

    openBtn.addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    overlay.addEventListener("click", close);
    document.addEventListener("keydown", (e)=>{
      if(e.key === "Escape") close();
    });
  }

  // -------------------------
  // Dropdowns (Desktop)
  // FIXED: does not disappear when moving cursor into dropdown items
  // -------------------------
  function initDropdowns(){
    const dds = $$("[data-dd]");
    if(!dds.length) return;

    // Keep small close timers per dropdown so the menu doesn't vanish
    // when the cursor moves from the button into the dropdown panel.
    const timers = new WeakMap();

    const closeOne = (dd) => {
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if(btn && menu){
        btn.setAttribute("aria-expanded","false");
        menu.classList.remove("open");
      }
    };

    const clearTimer = (dd) => {
      const t = timers.get(dd);
      if(t){
        clearTimeout(t);
        timers.delete(dd);
      }
    };

    const scheduleClose = (dd) => {
      clearTimer(dd);
      // delay prevents flicker when crossing tiny gaps
      timers.set(dd, setTimeout(() => {
        closeOne(dd);
        timers.delete(dd);
      }, 250));
    };

    const closeAll = () => {
      dds.forEach(dd=>{
        clearTimer(dd);
        closeOne(dd);
      });
    };

    dds.forEach(dd=>{
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if(!btn || !menu) return;

      btn.addEventListener("click",(e)=>{
        e.preventDefault();
        const open = menu.classList.contains("open");
        closeAll();
        if(!open){
          menu.classList.add("open");
          btn.setAttribute("aria-expanded","true");
        }
      });

      dd.addEventListener("mouseenter",()=>{
        if(window.matchMedia("(hover:hover)").matches){
          clearTimer(dd);
          closeAll();
          menu.classList.add("open");
          btn.setAttribute("aria-expanded","true");
        }
      });

      dd.addEventListener("mouseleave",()=>{
        if(window.matchMedia("(hover:hover)").matches){
          scheduleClose(dd);
        }
      });

      // If the cursor enters the menu, keep it open
      menu.addEventListener("mouseenter",()=> clearTimer(dd));
      menu.addEventListener("mousemove",()=> clearTimer(dd));
    });

    document.addEventListener("click",(e)=>{
      if(!e.target.closest("[data-dd]")) closeAll();
    });
    document.addEventListener("keydown",(e)=>{
      if(e.key==="Escape") closeAll();
    });
  }

  // -------------------------
  // FAQ accordion
  // -------------------------
  function initFAQ(){
    $$(".faq-btn").forEach(btn=>{
      btn.addEventListener("click",()=>{
        const expanded = btn.getAttribute("aria-expanded")==="true";
        btn.setAttribute("aria-expanded", expanded ? "false" : "true");
      });
    });
  }

  // -------------------------
  // Search (simple)
  // -------------------------
  function initSearch(){
    const input = $("#searchInput");
    const btn = $("#searchBtn");
    const wrap = $("#searchResults");
    if(!input || !btn || !wrap) return;

    const items = $$(".section-link").map(a => ({
      el: a,
      title: safe($(".t", a)?.textContent),
      desc: safe($(".d", a)?.textContent),
      href: a.getAttribute("href") || "#"
    }));

    const highlight = (text, q) => {
      if(!q) return text;
      const re = new RegExp(`(${escRE(q)})`, "ig");
      return text.replace(re, "<mark>$1</mark>");
    };

    const render = (q) => {
      const query = safe(q);
      if(!query){
        wrap.classList.remove("open");
        wrap.innerHTML = "";
        return;
      }

      const qLower = query.toLowerCase();
      const results = items.filter(it =>
        it.title.toLowerCase().includes(qLower) || it.desc.toLowerCase().includes(qLower)
      ).slice(0, 12);

      if(!results.length){
        wrap.classList.add("open");
        wrap.innerHTML = `<div class="result-meta">No results found for "<b>${query}</b>"</div>`;
        return;
      }

      wrap.classList.add("open");
      wrap.innerHTML = results.map(it => `
        <a class="result-item" href="${it.href}">
          <div>
            <div class="result-title">${highlight(it.title, query)}</div>
            <div class="result-meta">${highlight(it.desc, query)}</div>
          </div>
          <div class="result-meta">Open</div>
        </a>
      `).join("");
    };

    btn.addEventListener("click", ()=> render(input.value));
    input.addEventListener("keydown", (e)=>{
      if(e.key === "Enter") render(input.value);
    });
  }

  // ---- Homepage JSON render ----
  async function renderHomepage(){
    if(page !== "index.html") return;

    const leftCol = $("#leftCol");
    const rightCol = $("#rightCol");

    if(!leftCol || !rightCol) return;

    let data = null;
    try{
      const res = await fetch("index_data.json", { cache: "no-store" });
      if(!res.ok) throw new Error("index_data.json missing");
      data = await res.json();
    }catch(err){
      // do nothing if missing
      return;
    }

    if(!data || !Array.isArray(data.sections)) return;

    const renderSection = (section) => {
      const card = document.createElement("section");
      card.className = "section-card";

      const head = document.createElement("div");
      head.className = "section-head";
      head.style.background = section.color || "linear-gradient(90deg, #0ea5e9, #4f46e5)";

      const left = document.createElement("div");
      left.className = "left";
      left.innerHTML = `<i class="${safe(section.icon)}"></i><span>${safe(section.title)}</span>`;

      const right = document.createElement("a");
      right.className = "mini-links";
      right.href = normalizeUrl(section.moreUrl) || "#";
      right.textContent = safe(section.moreText) || "";
      right.rel = "noopener";
      right.style.display = section.moreText ? "inline-block" : "none";

      head.appendChild(left);
      head.appendChild(right);

      const body = document.createElement("div");
      body.className = "section-body";

      const list = document.createElement("div");
      list.className = "section-list";

      (section.items || []).forEach(item=>{
        const name = safe(item.name);
        const url = normalizeUrl(item.url);
        if(!name || !url) return;
        if(isHomePageCta(name, url)) return;

        const a = document.createElement("a");
        a.className = "section-link";
        a.href = url;
        a.rel = "noopener";
        a.innerHTML = `<div class="t">${name}</div><div class="d">${safe(item.desc)}</div>`;
        list.appendChild(a);
      });

      body.appendChild(list);
      card.appendChild(head);
      card.appendChild(body);

      return card;
    };

    // Build two columns
    leftCol.innerHTML = "";
    rightCol.innerHTML = "";

    data.sections.forEach((sec, idx)=>{
      const card = renderSection(sec);
      if(!card) return;
      (idx % 2 === 0 ? leftCol : rightCol).appendChild(card);
    });
  }

  // ---- Category page ----
  async function renderCategory(){
    if(page !== "category.html") return;

    const grid = $("#categoryGrid");
    const titleEl = $("#categoryTitle");
    const descEl = $("#categoryDesc");
    if(!grid) return;

    const params = new URLSearchParams(location.search);
    const group = safe(params.get("group"));

    let data = null;
    try{
      const res = await fetch("category_data.json", { cache: "no-store" });
      if(!res.ok) throw new Error("category_data.json missing");
      data = await res.json();
    }catch(err){
      return;
    }

    if(!data || !data.groups) return;

    const g = data.groups[group];
    if(!g){
      grid.innerHTML = `<div class="seo-block"><p>Category not found.</p></div>`;
      return;
    }

    if(titleEl) titleEl.textContent = safe(g.title) || "Category";
    if(descEl) descEl.textContent = safe(g.desc) || "";

    grid.innerHTML = "";
    (g.items || []).forEach(item=>{
      const name = safe(item.name);
      const url = normalizeUrl(item.url);
      if(!name || !url) return;

      const a = document.createElement("a");
      a.className = "section-link";
      a.href = url;
      a.rel = "noopener";
      a.innerHTML = `<div class="t">${name}</div><div class="d">${safe(item.desc)}</div>`;
      grid.appendChild(a);
    });
  }

  // ---- CSC services page ----
  async function renderServices(){
    // support both file names (your repo uses one of them)
    if(page !== "govt-services-2.html" && page !== "csc-services.html") return;

    const grid = $("#servicesGrid");
    if(!grid) return;

    let data = null;
    try{
      const res = await fetch("services_data.json", { cache: "no-store" });
      if(!res.ok) throw new Error("services_data.json missing");
      data = await res.json();
    }catch(err){
      return;
    }

    if(!data || !Array.isArray(data.items)) return;

    grid.innerHTML = "";
    data.items.forEach(item=>{
      const name = safe(item.name);
      const url = normalizeUrl(item.url);
      if(!name || !url) return;

      const a = document.createElement("a");
      a.className = "section-link";
      a.href = url;
      a.rel = "noopener";
      a.innerHTML = `<div class="t">${name}</div><div class="d">${safe(item.desc)}</div>`;
      grid.appendChild(a);
    });
  }

  // ---- Boot ----
  document.addEventListener("DOMContentLoaded", async ()=>{
    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    initFAQ();
    initSearch();

    await renderHomepage();
    await renderCategory();
    await renderServices();
  });

})();
