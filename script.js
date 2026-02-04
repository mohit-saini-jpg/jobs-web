(() => {
  "use strict";

  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const safe = (v) => (v ?? "").toString().trim();
  const escRE = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

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
  // Offcanvas menu (FIXED: always closes, no overlap)
  // -------------------------
  function initOffcanvas(){
    const btn = $("#menuBtn");
    const closeBtn = $("#closeMenuBtn");
    const menu = $("#mobileMenu");
    const overlay = $("#menuOverlay");

    if(!btn || !closeBtn || !menu || !overlay) return;

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

    // close on any menu link click
    menu.addEventListener("click", (e)=>{
      const a = e.target.closest("a");
      if(a) close();
    });

    document.addEventListener("keydown", (e)=>{
      if(e.key === "Escape") close();
    });

    // Safety: if overlay/menu ever mismatch, force close on resize
    window.addEventListener("resize", ()=>{
      if(window.innerWidth > 980) close();
    });

    // expose for debugging
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
  // Category pages (from jobs.json)
  // - requested 3-column layout: handled by CSS .cat-grid
  // - add SEO + FAQs automatically at bottom
  // -------------------------
  function normalizeGroup(g){
    const v=(g||"").toLowerCase().trim();
    const map={
      "study":"study",
      "study-wise":"study",
      "studywise":"study",
      "popular":"popular",
      "popular-jobs":"popular",
      "state":"state",
      "state-wise":"state",
      "statewise":"state",
      "admissions":"admissions",
      "admission":"admissions",
      "admit-result":"admit-result",
      "admitresult":"admit-result",
      "khabar":"khabar",
      "news":"khabar",
      "study-material":"study-material",
      "courses":"study-material"
    };
    return map[v] || v || "study";
  }

  function groupMeta(group){
    const meta={
      "study":{
        title:"Study wise jobs",
        desc:"Browse government job links by education level: 8th pass, 10th pass, 12th pass, ITI, diploma, graduation and more."
      },
      "popular":{
        title:"Popular job categories",
        desc:"Explore popular government job categories like SSC, Railway, Police, Bank, Teaching and more."
      },
      "state":{
        title:"State wise jobs",
        desc:"Find state-wise government job links and recruitment updates."
      },
      "admissions":{
        title:"Admissions",
        desc:"Admissions updates and official application links for universities, colleges and entrance exams."
      },
      "admit-result":{
        title:"Admit Card / Result / Answer Key / Syllabus",
        desc:"Quick access to admit cards, results, answer keys and syllabus links from official sources."
      },
      "khabar":{
        title:"Latest Khabar",
        desc:"Latest news and updates related to jobs, exams and government announcements."
      },
      "study-material":{
        title:"Study Material & Top Courses",
        desc:"Study resources, notes, preparation links and recommended courses for government exams."
      }
    };
    return meta[group] || { title:"Category", desc:"Browse useful links and categories." };
  }

  async function renderCategoryPage(){
    if(page !== "category.html") return;

    const params=new URLSearchParams(location.search);
    const group=normalizeGroup(params.get("group"));

    const meta=groupMeta(group);
    const titleEl=$("#categoryTitle");
    const descEl=$("#categoryDesc");
    const crumb=$("#crumbText");
    if(titleEl) titleEl.textContent = meta.title;
    if(descEl) descEl.textContent = meta.desc;
    if(crumb) crumb.textContent = meta.title;

    document.title = `${meta.title} | Top Sarkari Jobs`;

    let jobs=null;
    try{
      const r=await fetch("jobs.json",{ cache:"no-store" });
      if(r.ok) jobs=await r.json();
    }catch(_){}

    const grid=$("#categoryGrid");
    const empty=$("#categoryEmpty");
    const filter=$("#categoryFilter");
    const clear=$("#clearCategoryFilter");

    if(!grid) return;

    if(!jobs){
      grid.innerHTML="";
      if(empty) empty.style.display="block";
      return;
    }

    const pool=[]
      .concat(Array.isArray(jobs.top_jobs)?jobs.top_jobs:[])
      .concat(Array.isArray(jobs.left_jobs)?jobs.left_jobs:[])
      .concat(Array.isArray(jobs.right_jobs)?jobs.right_jobs:[]);

    // heading matchers (tune if your jobs.json headings differ)
    const matchers={
      "study":[/study/i],
      "popular":[/popular/i],
      "state":[/state/i],
      "admissions":[/admission/i],
      "admit-result":[/admit/i, /result/i, /answer/i, /syllabus/i],
      "khabar":[/khabar/i, /news/i],
      "study-material":[/study material/i, /course/i, /notes?/i]
    };

    const reList = matchers[group] || [/.*/];

    const blocks=[];
    let currentHeading=null;
    let items=[];

    const flush=()=>{
      if(currentHeading && items.length){
        blocks.push({ heading: currentHeading, items: items.slice() });
      }
      currentHeading=null;
      items=[];
    };

    for(const it of pool){
      if(it && typeof it.title==="string"){
        flush();
        const h=safe(it.title);
        const ok=reList.some(re=>re.test(h));
        currentHeading = ok ? h : null;
        continue;
      }
      if(!currentHeading) continue;

      const name=safe(it.name);
      const url=it.url || it.link || "";
      if(!name || !url) continue;

      items.push({ name, url, external: !!it.external });
    }
    flush();

    const render=(blocksToRender, q="")=>{
      grid.classList.add("cat-grid");
      grid.innerHTML="";

      if(!blocksToRender.length){
        if(empty) empty.style.display="block";
        return;
      }
      if(empty) empty.style.display="none";

      const colorMap={
        "study":"#2563eb",
        "popular":"#db2777",
        "state":"#059669",
        "admissions":"#f59e0b",
        "admit-result":"#ef4444",
        "khabar":"#7c3aed",
        "study-material":"#0ea5e9"
      };
      const color=colorMap[group] || "#0284c7";

      blocksToRender.forEach(b=>{
        const card=document.createElement("article");
        card.className="section-card";
        card.innerHTML=`
          <div class="section-head" style="background:${color}">
            <div class="left">
              <i class="fa-solid fa-layer-group"></i>
              <span>${safe(b.heading)}</span>
            </div>
          </div>
          <div class="section-body">
            <div class="section-list"></div>
          </div>
        `;

        const list=$(".section-list", card);
        b.items.forEach(x=>{
          const a=document.createElement("a");
          a.className="section-link";

          const href = x.external ? x.url : openInternal(x.url, x.name);
          a.href=href;
          if(x.external){ a.target="_blank"; a.rel="noopener"; }

          const qSafe=safe(q);
          const name = qSafe
            ? safe(x.name).replace(new RegExp(`(${escRE(qSafe)})`, "ig"), "<mark>$1</mark>")
            : safe(x.name);

          a.innerHTML=`
            <div class="t">${name}</div>
            <div class="d">Open official link</div>
          `;
          list.appendChild(a);
        });

        grid.appendChild(card);
      });

      // SEO + FAQs appended under grid
      renderCategorySEO(meta.title, meta.desc, group);
    };

    render(blocks);

    if(filter){
      filter.addEventListener("input", ()=>{
        const q=safe(filter.value).toLowerCase();
        if(!q){ render(blocks); return; }
        const filtered = blocks
          .map(b=>({ heading:b.heading, items:b.items.filter(x=>safe(x.name).toLowerCase().includes(q)) }))
          .filter(b=>b.items.length);
        render(filtered, q);
      });
    }

    if(clear){
      clear.addEventListener("click", ()=>{
        if(!filter) return;
        filter.value="";
        render(blocks);
        filter.focus();
      });
    }
  }

  function renderCategorySEO(title, desc, group){
    // Remove old SEO block if re-rendering
    const old=$("#categorySEO");
    if(old) old.remove();

    const main=$("#main");
    if(!main) return;

    const wrap=document.createElement("section");
    wrap.id="categorySEO";
    wrap.className="seo-block";
    wrap.innerHTML=`
      <h2>${title} – quick guide</h2>
      <p>${desc}</p>

      <div class="seo-grid">
        <div class="seo-card">
          <h3>How to use this page</h3>
          <ul>
            <li>Use the filter box to find a link faster.</li>
            <li>Open the official link and confirm eligibility & dates.</li>
            <li>Bookmark this page for quick access to updates.</li>
          </ul>
        </div>

        <div class="seo-card">
          <h3>Tips to avoid mistakes</h3>
          <ul>
            <li>Always apply from the official website.</li>
            <li>Check last date, fee, and required documents carefully.</li>
            <li>Keep your registration number and DOB ready for results/admit cards.</li>
          </ul>
        </div>
      </div>

      <div class="faq-wrap">
        <div class="faq-card" style="box-shadow:none;border:1px solid var(--line);">
          <h2>FAQs – ${title}</h2>
          <p class="faq-sub">Common questions related to ${title.toLowerCase()}.</p>

          <div class="faq-item">
            <button type="button" class="faq-btn" aria-expanded="false">
              <span>Are these links official?</span>
              <i class="fas fa-chevron-down"></i>
            </button>
            <div class="faq-panel" hidden>
              We aim to list official and trusted sources. Always verify details on the official portal before applying or downloading documents.
            </div>
          </div>

          <div class="faq-item">
            <button type="button" class="faq-btn" aria-expanded="false">
              <span>Why do dates sometimes change?</span>
              <i class="fas fa-chevron-down"></i>
            </button>
            <div class="faq-panel" hidden>
              Recruiting boards may revise schedules. Check the official notice for the latest updates.
            </div>
          </div>

          <div class="faq-item">
            <button type="button" class="faq-btn" aria-expanded="false">
              <span>How can I find a specific item quickly?</span>
              <i class="fas fa-chevron-down"></i>
            </button>
            <div class="faq-panel" hidden>
              Use the filter box on this page or the main site search at the top to locate jobs, results, admit cards, and categories.
            </div>
          </div>
        </div>
      </div>
    `;
    main.appendChild(wrap);

    // re-bind FAQ buttons inside the injected block
    initFAQ();
  }

  // -------------------------
  // CSC Services page (govt-services.html)
  // Rebuild the missing list from services.json
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

    // Render as clean cards
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
  // Tools page (tools.html)
  // Render tools.json (image/pdf/video arrays)
  // -------------------------
  async function renderToolsPage(){
    if(page !== "tools.html") return;

    const grid=$("#toolsGrid");
    if(!grid) return;

    let data=null;
    try{
      const r=await fetch("tools.json",{ cache:"no-store" });
      if(r.ok) data=await r.json();
    }catch(_){}

    grid.innerHTML="";
    grid.classList.add("cat-grid");

    const buckets = [
      { key:"image", title:"Image Tools", color:"#0ea5e9" },
      { key:"pdf", title:"PDF Tools", color:"#4f46e5" },
      { key:"video", title:"Video Tools", color:"#db2777" }
    ];

    let any=false;

    buckets.forEach(b=>{
      const items = (data && Array.isArray(data[b.key])) ? data[b.key] : [];
      if(!items.length) return;
      any=true;

      const card=document.createElement("article");
      card.className="section-card";
      card.innerHTML=`
        <div class="section-head" style="background:${b.color}">
          <div class="left">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
            <span>${b.title}</span>
          </div>
        </div>
        <div class="section-body">
          <div class="section-list"></div>
        </div>
      `;
      const list=$(".section-list", card);

      items.forEach(it=>{
        const name=safe(it.name);
        const url=it.url || it.link || "";
        if(!name || !url) return;

        const a=document.createElement("a");
        a.className="section-link";
        a.href = it.external ? url : openInternal(url, name);
        if(it.external){ a.target="_blank"; a.rel="noopener"; }
        a.innerHTML = `<div class="t">${name}</div><div class="d">Open tool</div>`;
        list.appendChild(a);
      });

      grid.appendChild(card);
    });

    if(!any){
      grid.innerHTML = `<div class="seo-block"><strong>No tools found.</strong><p>Please check tools.json.</p></div>`;
    }
  }

  // -------------------------
  // Site search (fast index)
  // -------------------------
  let SEARCH_INDEX = [];
  let SEARCH_READY = false;

  async function buildSearchIndex(){
    if(SEARCH_READY) return;

    const out=[];

    // dynamic sections
    try{
      const r=await fetch("dynamic-sections.json",{ cache:"no-store" });
      if(r.ok){
        const d=await r.json();
        (d.sections||[]).forEach(sec=>{
          (sec.items||[]).forEach(it=>{
            const title=safe(it.name);
            const url=it.url||it.link||"";
            if(!title || !url) return;
            out.push({
              title,
              meta: safe(sec.title)||"Updates",
              href: it.external ? url : openInternal(url, title),
              external: !!it.external
            });
          });
        });
      }
    }catch(_){}

    // jobs.json (all links)
    try{
      const r=await fetch("jobs.json",{ cache:"no-store" });
      if(r.ok){
        const j=await r.json();
        const pool=[...(j.top_jobs||[]), ...(j.left_jobs||[]), ...(j.right_jobs||[])];
        pool.forEach(it=>{
          if(it && it.title) return;
          const title=safe(it.name);
          const url=it.url||it.link||"";
          if(!title || !url) return;
          out.push({
            title,
            meta:"Jobs / Categories",
            href: it.external ? url : openInternal(url, title),
            external: !!it.external
          });
        });
      }
    }catch(_){}

    // tools.json
    try{
      const r=await fetch("tools.json",{ cache:"no-store" });
      if(r.ok){
        const t=await r.json();
        ["image","pdf","video"].forEach(k=>{
          (t[k]||[]).forEach(it=>{
            const title=safe(it.name);
            const url=it.url||it.link||"";
            if(!title || !url) return;
            out.push({
              title,
              meta:"Tools",
              href: it.external ? url : openInternal(url, title),
              external: !!it.external
            });
          });
        });
      }
    }catch(_){}

    // services.json (titles only)
    try{
      const r=await fetch("services.json",{ cache:"no-store" });
      if(r.ok){
        const s=await r.json();
        const services=(s.services||s||[]);
        (services||[]).forEach(it=>{
          const title=safe(it.name||it.service);
          if(!title) return;
          out.push({
            title,
            meta:"CSC Services",
            href:"govt-services.html",
            external:false
          });
        });
      }
    }catch(_){}

    // de-dup
    const seen=new Set();
    SEARCH_INDEX = out.filter(x=>{
      const k=(x.title+"|"+x.href).toLowerCase();
      if(seen.has(k)) return false;
      seen.add(k);
      return true;
    });

    SEARCH_READY=true;
  }

  function initSearch(){
    const input=$("#siteSearchInput");
    const btn=$("#siteSearchBtn");
    const results=$("#searchResults");
    const openBtn=$("#openSearchBtn");

    if(!input || !btn || !results) return;

    const run = async ()=>{
      const q=safe(input.value);
      if(!q){
        results.classList.remove("open");
        results.innerHTML="";
        return;
      }

      await buildSearchIndex();

      const ql=q.toLowerCase();
      const matches = SEARCH_INDEX
        .filter(x => x.title.toLowerCase().includes(ql) || x.meta.toLowerCase().includes(ql))
        .slice(0,25);

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
