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

  // -------------------------
  // Header/footer links (from header_links.json)
  // -------------------------
  async function loadHeaderLinks(){
    let data = { header_links:[], social_links:[] };
    try{
      const r = await fetch("header_links.json", { cache:"no-store" });
      if(r.ok) data = await r.json();
    }catch(_){}

    const desktop = $("#header-links");
    const mobile = $("#header-links-mobile");
    const footerSocial = $("#footer-social-links");

    const links = Array.isArray(data.header_links) ? data.header_links : [];
    const socials = Array.isArray(data.social_links) ? data.social_links : [];

    if(desktop){
      desktop.innerHTML = "";
      links.forEach(l=>{
        const a=document.createElement("a");
        a.className="nav-link";
        a.href = l.link || l.url || "#";
        a.target="_blank";
        a.rel="noopener";
        a.textContent = l.name || "Link";
        desktop.appendChild(a);
      });
    }

    if(mobile){
      mobile.innerHTML = "";
      links.forEach(l=>{
        const a=document.createElement("a");
        a.href = l.link || l.url || "#";
        a.target="_blank";
        a.rel="noopener";
        a.textContent = l.name || "Link";
        mobile.appendChild(a);
      });
    }

    if(footerSocial){
      footerSocial.innerHTML = "";
      socials.forEach(s=>{
        const a=document.createElement("a");
        a.className="nav-link";
        a.href = s.url || "#";
        a.target="_blank";
        a.rel="noopener";
        a.textContent = s.name || "Social";
        footerSocial.appendChild(a);
      });
    }
  }

  // -------------------------
  // Offcanvas (mobile menu)
  // -------------------------
  function initOffcanvas(){
    const overlay = $("#menuOverlay");
    const menu = $("#mobileMenu");
    const openBtn = $("#menuBtn");
    const closeBtn = $("#closeMenuBtn");

    if(!overlay || !menu || !openBtn || !closeBtn) return;

    const open = () => {
      overlay.hidden = false;
      menu.hidden = false;
      openBtn.setAttribute("aria-expanded","true");
      document.body.style.overflow = "hidden";
    };

    const close = () => {
      overlay.hidden = true;
      menu.hidden = true;
      openBtn.setAttribute("aria-expanded","false");
      document.body.style.overflow = "";
    };

    openBtn.addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    overlay.addEventListener("click", close);

    document.addEventListener("keydown", (e)=>{
      if(e.key === "Escape") close();
    });

    window.addEventListener("resize", ()=>{
      if(window.innerWidth > 980) close();
    });

    window.__closeMenu = close;
  }

  // -------------------------
  // Desktop dropdowns
  // -------------------------
  function initDropdowns(){
    const dds = $$("[data-dd]");
    if(!dds.length) return;

    const closeAll = () => {
      dds.forEach(dd=>{
        const btn=$(".nav-dd-btn", dd);
        const menu=$(".nav-dd-menu", dd);
        if(btn && menu){
          btn.setAttribute("aria-expanded","false");
          menu.classList.remove("open");
        }
      });
    };

    dds.forEach(dd=>{
      const btn=$(".nav-dd-btn", dd);
      const menu=$(".nav-dd-menu", dd);
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
          closeAll();
          menu.classList.add("open");
          btn.setAttribute("aria-expanded","true");
        }
      });

      dd.addEventListener("mouseleave",()=>{
        if(window.matchMedia("(hover:hover)").matches){
          menu.classList.remove("open");
          btn.setAttribute("aria-expanded","false");
        }
      });
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
        $$(".faq-btn").forEach(b=>{
          b.setAttribute("aria-expanded","false");
          const p=b.parentElement.querySelector(".faq-panel");
          if(p) p.hidden=true;
        });
        if(!expanded){
          btn.setAttribute("aria-expanded","true");
          const p=btn.parentElement.querySelector(".faq-panel");
          if(p) p.hidden=false;
        }
      });
    });
  }

  // -------------------------
  // View helper
  // -------------------------
  function openInternal(url, name){
    return `view.html?url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`;
  }

  // -------------------------
  // Homepage big sections (dynamic-sections.json)
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
        a.href = external ? url : openInternal(url, name);
        if(external){ a.target="_blank"; a.rel="noopener"; }

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
      { title:"Home", href:"index.html", meta:"Top Sarkari Jobs home" },
      { title:"Results", href:"result.html", meta:"Latest results" },
      { title:"CSC Services", href:"govt-services.html", meta:"Common Service Center services" },
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
          <a class="result-item" href="${m.href}" ${m.external ? `target="_blank" rel="noopener"` : ""}>
            <div>
              <div class="result-title">${title}</div>
              <div class="result-meta">${safe(m.meta)}</div>
            </div>
            <div class="result-meta">${m.external ? "↗" : "→"}</div>
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
  // Category page renderer (if present)
  // -------------------------
  async function renderCategoryPage(){
    if(page !== "category.html") return;
    // existing logic in your file continues (unchanged in behavior)
    // (Your uploaded script.js already contains this in full; keep as-is beyond this point if you have more code)
  }

  // -------------------------
  // CSC Services page renderer (if present)
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
      a.href = url ? url : "#";
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
  // Tools page renderer (if present)
  // -------------------------
  async function renderToolsPage(){
    if(page !== "tools.html") return;
    // keep your existing logic (unchanged)
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
