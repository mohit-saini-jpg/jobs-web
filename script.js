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
    return (
      n.includes("website का main home page") ||
      n.includes("main home page") ||
      (n.includes("🏠") && n.includes("home page")) ||
      n.includes("╰┈➤") ||
      (u.includes("topsarkarijobs.com") && (n.includes("home page") || n.includes("main home")))
    );
  };

  // -------------------------
  // URL helpers (IMPORTANT: don't break internal links)
  // -------------------------
  function isExternalUrl(u){
    return /^https?:\/\//i.test(u) || /^\/\//.test(u) || /^www\./i.test(u);
  }

  function normalizeExternal(u){
    const s = safe(u);
    if(!s) return "";
    if(/^https?:\/\//i.test(s)) return s;
    if(/^\/\//.test(s)) return "https:" + s;
    if(/^www\./i.test(s)) return "https://" + s;
    return s;
  }

  // Use view.html iframe wrapper ONLY for true external URLs.
  // If the URL is already an internal page/link, keep it untouched.
  function openInternal(url, name){
    const u = safe(url);
    if(!u) return "#";
    if(isExternalUrl(u)){
      const nu = normalizeExternal(u);
      return `view.html?url=${encodeURIComponent(nu)}&name=${encodeURIComponent(safe(name))}`;
    }
    return u; // internal relative link
  }

  // -------------------------
  // Header/footer links (from header_links.json)
  // -------------------------
  async function loadHeaderLinks(){
    let data = { header_links:[], social_links:[] };
    try{
      const r = await fetch("header_links.json", { cache:"no-store" });
      if(r.ok) data = await r.json();
    }catch(_){}

    const desktop = $("#desktopHeaderLinks");
    const mobile = $("#mobileHeaderLinks");

    const links = Array.isArray(data.header_links) ? data.header_links : [];
    if(desktop) desktop.innerHTML = "";
    if(mobile) mobile.innerHTML = "";

    links.forEach(l=>{
      const text = safe(l.name || l.title || l.text);
      const url  = safe(l.url || l.href || l.link);
      if(!text || !url) return;

      const a1 = document.createElement("a");
      a1.className = "toplink";
      a1.href = openInternal(url, text);

      const a2 = a1.cloneNode();
      a2.className = "toplink";

      a1.textContent = text;
      a2.textContent = text;

      if(desktop) desktop.appendChild(a1);
      if(mobile) mobile.appendChild(a2);
    });
  }

  // -------------------------
  // Offcanvas menu
  // -------------------------
  function initOffcanvas(){
    const btn = $("#menuBtn");
    const oc  = $("#offcanvas");
    const close = $("#offClose");

    if(!btn || !oc) return;

    const open = ()=> oc.classList.add("open");
    const shut = ()=> oc.classList.remove("open");

    btn.addEventListener("click", open);
    if(close) close.addEventListener("click", shut);

    document.addEventListener("click", (e)=>{
      if(!oc.classList.contains("open")) return;
      if(e.target.closest("#offcanvas")) return;
      if(e.target.closest("#menuBtn")) return;
      shut();
    });

    document.addEventListener("keydown",(e)=>{
      if(e.key === "Escape") shut();
    });
  }

  // -------------------------
  // Dropdowns (click toggle)
  // -------------------------
  function initDropdowns(){
    $$(".nav-dd").forEach(dd=>{
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if(!btn || !menu) return;

      const toggle = ()=>{
        const isOpen = menu.classList.toggle("open");
        dd.setAttribute("aria-expanded", String(isOpen));
      };

      btn.addEventListener("click", (e)=>{
        e.preventDefault();
        e.stopPropagation();
        toggle();
      });

      document.addEventListener("click", (e)=>{
        if(!dd.contains(e.target)){
          menu.classList.remove("open");
          dd.setAttribute("aria-expanded", "false");
        }
      });

      dd.addEventListener("keydown", (e)=>{
        if(e.key === "Escape"){
          menu.classList.remove("open");
          dd.setAttribute("aria-expanded", "false");
          btn.blur();
        }
      });
    });
  }

  // -------------------------
  // FAQ accordion
  // -------------------------
  function initFAQ(){
    $$(".faq-item").forEach(item=>{
      const head = $(".faq-q", item);
      const body = $(".faq-a", item);
      if(!head || !body) return;

      head.addEventListener("click", ()=>{
        item.classList.toggle("open");
      });
    });
  }

  // -------------------------
  // Homepage dynamic sections
  // -------------------------
  async function renderHomepageSections(){
    const wrap = $("#dynamic-sections");
    if(!wrap) return;

    let data={ sections:[] };
    try{
      const r=await fetch("dynamic-sections.json",{ cache:"no-store" });
      if(r.ok) data=await r.json();
    }catch(_){}

    wrap.innerHTML="";

    (data.sections||[]).forEach(sec=>{
      const title=safe(sec.title)||"Updates";
      const color=safe(sec.color)||"#0284c7";
      const icon=safe(sec.icon)||"fa-solid fa-briefcase";

      const card=document.createElement("article");
      card.className="section-card";
      card.innerHTML=`
        <div class="section-head" style="background:${color}">
          <div class="left">
            <i class="${icon}"></i>
            <span>${title}</span>
          </div>
        </div>
        <div class="section-body">
          <div class="section-list"></div>
          ${sec.viewMoreUrl ? `<a class="view-all" href="${openInternal(sec.viewMoreUrl, title)}">View All <i class="fa-solid fa-arrow-right"></i></a>` : ""}
        </div>
      `;

      const list=$(".section-list", card);
      const items=Array.isArray(sec.items) ? sec.items.slice(0,8) : [];
      items.forEach(it=>{
        const name=safe(it.name)||"Open";
        const url=it.url||it.link||"";
        if(!url) return;

        if(isHomePageCta(name, url)) return;

        const external=!!it.external;

        const a=document.createElement("a");
        a.className="section-link";

        // If external flag set, open raw. Otherwise route correctly:
        // - external URLs => view.html wrapper
        // - internal URLs => keep as-is
        a.href = external ? normalizeExternal(url) : openInternal(url, name);

        if(external){
          a.target="_blank";
          a.rel="noopener";
        }

        a.innerHTML=`
          <div class="t">${name}</div>
          ${it.date ? `<div class="d">${safe(it.date)}</div>` : `<div class="d">Open official link</div>`}
        `;
        list.appendChild(a);
      });

      wrap.appendChild(card);
    });
  }

  // -------------------------
  // Search
  // -------------------------
  function initSearch(){
    const input = $("#siteSearchInput");
    const btn = $("#siteSearchBtn");
    const results = $("#searchResults");
    const openBtn = $("#openSearchBtn");

    if(!input || !btn || !results) return;

    const index = [
      { title:"Home", href:"index.html", meta:"Homepage" },
      { title:"Results", href:"result.html", meta:"Results and updates" },
      { title:"Search", href:"search.html", meta:"Search jobs & pages" },
      { title:"CSC Services", href:"govt-services.html", meta:"Government services" },
      { title:"Tools", href:"tools.html", meta:"Useful tools" },
      { title:"Helpdesk", href:"helpdesk.html", meta:"Support and guides" },
      { title:"Study wise jobs", href:"category.html?group=study", meta:"Jobs by education level" },
      { title:"Popular job categories", href:"category.html?group=popular", meta:"Top categories" },
      { title:"State wise jobs", href:"category.html?group=state", meta:"Jobs by state" },
      { title:"Admissions", href:"category.html?group=admissions", meta:"Admissions and forms" },
      { title:"Admit Card / Result / Answer Key / Syllabus", href:"category.html?group=admit-result", meta:"Admit/result/syllabus" },
      { title:"Latest Khabar", href:"category.html?group=khabar", meta:"News & updates" },
      { title:"Study Material & Top Courses", href:"category.html?group=study-material", meta:"Courses & material" }
    ];

    const run = () => {
      const q = safe(input.value).toLowerCase();
      if(!q){
        results.classList.remove("open");
        results.innerHTML="";
        return;
      }

      const matches = index.filter(x =>
        safe(x.title).toLowerCase().includes(q) ||
        safe(x.meta).toLowerCase().includes(q)
      ).slice(0, 12);

      if(!matches.length){
        results.classList.add("open");
        results.innerHTML = `
          <div class="result-item">
            <div>
              <div class="result-title">No results found</div>
              <div class="result-meta">Try a different keyword.</div>
            </div>
          </div>
        `;
        return;
      }

      const re=new RegExp(`(${escRE(q)})`, "ig");
      results.classList.add("open");
      results.innerHTML = matches.map(m=>{
        const title = safe(m.title).replace(re, "<mark>$1</mark>");
        return `
          <a class="result-item" href="${m.href}">
            <div>
              <div class="result-title">${title}</div>
              <div class="result-meta">${safe(m.meta)}</div>
            </div>
            <div class="result-meta">→</div>
          </a>
        `;
      }).join("");
    };

    btn.addEventListener("click", run);
    input.addEventListener("input", debounce(run, 150));
    input.addEventListener("keydown",(e)=>{
      if(e.key==="Enter") run();
      if(e.key==="Escape"){
        results.classList.remove("open");
        results.innerHTML="";
        input.blur();
      }
    });

    document.addEventListener("click",(e)=>{
      if(!e.target.closest(".search-card")){
        results.classList.remove("open");
      }
    });

    if(openBtn){
      openBtn.addEventListener("click", ()=>{
        input.scrollIntoView({ behavior:"smooth", block:"center" });
        setTimeout(()=>input.focus(), 150);
      });
    }
  }

  function debounce(fn, wait){
    let t=null;
    return (...args)=>{
      clearTimeout(t);
      t=setTimeout(()=>fn(...args), wait);
    };
  }

  // -------------------------
  // Category page renderer (FIXED)
  // -------------------------
  async function renderCategoryPage(){
    if(page !== "category.html") return;

    const grid = $("#categoryGrid");
    const titleEl = $("#categoryTitle");
    if(!grid) return;

    const params = new URLSearchParams(location.search);
    const group = safe(params.get("group")) || "study";

    const groupTitles = {
      "study":"Study wise jobs",
      "popular":"Popular job categories",
      "state":"State wise jobs",
      "admissions":"Admissions",
      "admit-result":"Admit Card / Result / Answer Key / Syllabus",
      "khabar":"Latest Khabar",
      "study-material":"Study Material & Top Courses"
    };
    if(titleEl) titleEl.textContent = groupTitles[group] || "Category";

    let data = {};
    try{
      const r = await fetch("dynamic-sections.json", { cache:"no-store" });
      if(r.ok) data = await r.json();
    }catch(_){}

    let items = null;

    // Shape A: { categories: { study:[...], popular:[...], ... } }
    if(data && data.categories && Array.isArray(data.categories[group])){
      items = data.categories[group];
    }

    // Shape B: { category_groups: [ { id/slug/group:'study', items:[...] }, ... ] }
    if(!items && Array.isArray(data.category_groups)){
      const g = data.category_groups.find(x =>
        safe(x.id).toLowerCase()===group ||
        safe(x.slug).toLowerCase()===group ||
        safe(x.group).toLowerCase()===group ||
        safe(x.key).toLowerCase()===group
      );
      if(g && Array.isArray(g.items)) items = g.items;
    }

    // Shape C: embedded as sections with a matching key
    if(!items && Array.isArray(data.sections)){
      const g = data.sections.find(x =>
        safe(x.group).toLowerCase()===group ||
        safe(x.key).toLowerCase()===group ||
        safe(x.id).toLowerCase()===group
      );
      if(g && Array.isArray(g.items)) items = g.items;
    }

    grid.innerHTML = "";

    if(!Array.isArray(items) || !items.length){
      grid.innerHTML = `<div class="seo-block"><strong>No items found.</strong><p>Please verify <code>dynamic-sections.json</code> contains category items for group: <code>${group}</code>.</p></div>`;
      return;
    }

    items.forEach(it=>{
      const name = safe(it.name || it.title || it.label);
      if(!name) return;

      // Prefer explicit href if provided, else url/link, else build from section id.
      const rawHref =
        it.href ||
        it.page ||
        it.url ||
        it.link ||
        (it.section ? `view.html?section=${encodeURIComponent(safe(it.section))}&name=${encodeURIComponent(name)}` : "");

      if(!rawHref) return;

      const a = document.createElement("a");
      a.className = "cat-card";

      // CRITICAL FIX:
      // - external URLs => view.html wrapper
      // - internal links (like view.html?section=..., search.html?... etc) => unchanged
      a.href = openInternal(rawHref, name);

      a.innerHTML = `
        <div class="cat-title">${name}</div>
        <div class="cat-meta">${safe(it.meta || it.desc || it.description || "Open")}</div>
      `;
      grid.appendChild(a);
    });
  }

  // -------------------------
  // CSC Services page renderer
  // -------------------------
  async function renderServicesPage(){
    if(page !== "govt-services.html") return;

    const list=$("#servicesList");
    if(!list) return;

    let data=null;
    try{
      const r=await fetch("services.json",{ cache:"no-store" });
      if(r.ok) data=await r.json();
    }catch(_){}

    const services = (data && (data.services || data)) || [];
    list.innerHTML="";

    if(!Array.isArray(services) || !services.length){
      list.innerHTML = `<div class="seo-block"><strong>No services found.</strong><p>Please check services.json.</p></div>`;
      return;
    }

    services.forEach(s=>{
      const name=safe(s.name || s.service);
      const url=s.url || s.link || "";
      if(!name) return;

      const a=document.createElement("a");
      a.className="section-link";
      a.href = url ? normalizeExternal(url) : "#";
      a.target = "_blank";
      a.rel="noopener";
      a.innerHTML = `
        <div class="t">${name}</div>
        <div class="d">Open service</div>
      `;
      list.appendChild(a);
    });
  }

  // -------------------------
  // Tools page renderer
  // -------------------------
  async function renderToolsPage(){
    if(page !== "tools.html") return;

    const list = $("#toolsList");
    if(!list) return;

    let data=null;
    try{
      const r=await fetch("tools.json",{ cache:"no-store" });
      if(r.ok) data=await r.json();
    }catch(_){}

    const tools = (data && (data.tools || data)) || [];
    list.innerHTML="";

    if(!Array.isArray(tools) || !tools.length){
      list.innerHTML = `<div class="seo-block"><strong>No tools found.</strong><p>Please check tools.json.</p></div>`;
      return;
    }

    tools.forEach(t=>{
      const name=safe(t.name || t.title);
      const url=t.url || t.link || "";
      if(!name || !url) return;

      const a=document.createElement("a");
      a.className="section-link";
      a.href = openInternal(url, name);
      a.innerHTML = `
        <div class="t">${name}</div>
        <div class="d">${safe(t.desc || t.description || "Open")}</div>
      `;
      list.appendChild(a);
    });
  }

  // -------------------------
  // Boot
  // -------------------------
  document.addEventListener("DOMContentLoaded", async ()=>{
    await loadHeaderLinks();
    initOffcanvas();
    initDropdowns();
    initFAQ();
    initSearch();

    if(page==="index.html" || page===""){
      await renderHomepageSections();
    }

    await renderCategoryPage();
    await renderServicesPage();
    await renderToolsPage();
  });

})();
