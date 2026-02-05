(() => {
  "use strict";

  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const safe = (v) => (v ?? "").toString().trim();
  const escRE = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  // ---- URL normalization (fixes links missing scheme like "www.*" or "csc.gov.in") ----
  function normalizeUrl(raw){
    const s = safe(raw);
    if(!s) return "";
    // already absolute or special scheme
    if(/^(https?:)?\/\//i.test(s) || /^(mailto:|tel:)/i.test(s)) return s;
    // hash / query only
    if(s.startsWith("#") || s.startsWith("?")) return s;
    // internal relative paths should stay as-is
    if(s.startsWith("/") || s.endsWith(".html") || s.startsWith("./") || s.startsWith("../")) return s;
    // plain domain / www / without scheme
    return "https://" + s.replace(/^\/+/, "");
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
        a.href = normalizeUrl(l.link || l.url || "#");
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
        a.href = normalizeUrl(l.link || l.url || "#");
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
        a.href = normalizeUrl(s.url || "#");
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
      const btn = $(".nav-dd-btn", dd);
      const menu = $(".nav-dd-menu", dd);
      if(btn && menu){
        btn.setAttribute("aria-expanded","false");
        menu.classList.remove("open");
      }
      dd.__ddCloseTimer && clearTimeout(dd.__ddCloseTimer);
      dd.__ddCloseTimer = null;
      dd.__ddHoveringMenu = false;
    });
  };

  dds.forEach(dd=>{
    const btn = $(".nav-dd-btn", dd);
    const menu = $(".nav-dd-menu", dd);
    if(!btn || !menu) return;

    // track when cursor is inside the menu (prevents instant close)
    menu.addEventListener("mouseenter", () => { dd.__ddHoveringMenu = true; });
    menu.addEventListener("mouseleave", () => {
      dd.__ddHoveringMenu = false;
      // close shortly after leaving menu
      dd.__ddCloseTimer && clearTimeout(dd.__ddCloseTimer);
      dd.__ddCloseTimer = setTimeout(() => {
        if(!dd.__ddHoveringMenu){
          menu.classList.remove("open");
          btn.setAttribute("aria-expanded","false");
        }
      }, 120);
    });

    // click to toggle (works on all devices)
    btn.addEventListener("click",(e)=>{
      e.preventDefault();
      const isOpen = menu.classList.contains("open");
      closeAll();
      if(!isOpen){
        menu.classList.add("open");
        btn.setAttribute("aria-expanded","true");
      }
    });

    // hover open for desktop
    dd.addEventListener("mouseenter", ()=>{
      if(window.matchMedia("(hover:hover)").matches){
        dd.__ddCloseTimer && clearTimeout(dd.__ddCloseTimer);
        dd.__ddCloseTimer = null;
        closeAll();
        menu.classList.add("open");
        btn.setAttribute("aria-expanded","true");
      }
    });

    // hover close with delay (so moving into the menu doesn't collapse it)
    dd.addEventListener("mouseleave", ()=>{
      if(window.matchMedia("(hover:hover)").matches){
        dd.__ddCloseTimer && clearTimeout(dd.__ddCloseTimer);
        dd.__ddCloseTimer = setTimeout(() => {
          if(!dd.__ddHoveringMenu){
            menu.classList.remove("open");
            btn.setAttribute("aria-expanded","false");
          }
        }, 120);
      }
    });
  });

  // close when clicking outside
  document.addEventListener("click",(e)=>{
    if(!e.target.closest("[data-dd]")) closeAll();
  });

  // close on escape
  document.addEventListener("keydown",(e)=>{
    if(e.key==="Escape") closeAll();
  });
}

  // -------------------------
  // View helper
  // -------------------------
  function openInternal(url, name){
    const u = normalizeUrl(url);
    return `view.html?url=${encodeURIComponent(u)}&name=${encodeURIComponent(name)}`;
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
        a.href = external ? normalizeUrl(url) : openInternal(url, name);
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
  // -------------------------
  function normalizeGroup(g){
    const v=(g||"").toLowerCase().trim();
    const map={
      "study":"study",
      "study-wise":"study",
      "studywise":"study",
      "popular":"popular",
      "popular-jobs":"popular",
      "categories":"popular",
      "state":"state",
      "state-wise":"state",
      "statewise":"state",
      "admissions":"admissions",
      "admit-result":"admit-result",
      "admit card":"admit-result",
      "admit":"admit-result",
      "result":"admit-result",
      "answer":"admit-result",
      "syllabus":"admit-result",
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

    const params = new URLSearchParams(location.search);
    const group = normalizeGroup(params.get("group"));

    const meta = groupMeta(group);
    const titleEl = $("#categoryTitle");
    const descEl = $("#categoryDesc");
    const crumb = $("#crumbText");

    if(titleEl) titleEl.textContent = meta.title;
    if(descEl) descEl.textContent = meta.desc;
    if(crumb) crumb.textContent = meta.title;

    document.title = `${meta.title} | Top Sarkari Jobs`;

    // ---- Load jobs.json (this is the original source of these lists) ----
    let jobs = null;
    try{
      const r = await fetch("jobs.json", { cache:"no-store" });
      if(r.ok) jobs = await r.json();
    }catch(_){}

    const grid = $("#categoryGrid");
    const empty = $("#categoryEmpty");
    const filter = $("#categoryFilter");
    const clear = $("#clearCategoryFilter");

    if(!grid) return;

    if(!jobs){
      grid.innerHTML = "";
      if(empty) empty.style.display = "block";
      return;
    }

    // ---- Robustly build a single pool of items, regardless of jobs.json shape ----
    const pool = [];

    if(Array.isArray(jobs)){
      pool.push(...jobs);
    }else if(jobs && typeof jobs === "object"){
      // tolerate any top-level arrays (future-proof)
      Object.keys(jobs).forEach(k=>{
        const v = jobs[k];
        if(Array.isArray(v)) pool.push(...v);
      });

      // tolerate nested buckets like { data: {...} } or { jobs: {...} }
      ["data","jobs","payload"].forEach(k=>{
        const v = jobs && jobs[k];
        if(v && typeof v === "object"){
          Object.keys(v).forEach(kk=>{
            const vv = v[kk];
            if(Array.isArray(vv)) pool.push(...vv);
          });
        }
      });
    }

    if(!pool.length){
      grid.innerHTML = "";
      if(empty) empty.style.display = "block";
      return;
    }

    // ---- Turn the pool into "sections" using title separators (same structure as homepage lists) ----
    const sections = [];
    let current = null;

    const startSection = (heading) => {
      const h = safe(heading);
      if(!h) return;
      current = { heading: h, items: [] };
      sections.push(current);
    };

    const pushItem = (name, url, external) => {
      if(!current) startSection(meta.title);
      const n = safe(name);
      const u = safe(url);
      if(!n || !u) return;
      current.items.push({ name: n, url: u, external: !!external });
    };

    pool.forEach(it=>{
      if(!it) return;

      const title = (typeof it.title === "string" && it.title) ||
                    (typeof it.heading === "string" && it.heading) ||
                    (typeof it.section === "string" && it.section);

      if(title){
        startSection(title);
        return;
      }

      const name = it.name || it.label || it.text;
      const url = it.url || it.link || it.href;
      if(name && url) pushItem(name, url, it.external);
    });

    const nonEmptySections = sections.filter(s => s.items && s.items.length);

    const containsAny = (hay, needles) => {
      const h = safe(hay).toLowerCase();
      return needles.some(n => h.includes(n));
    };

    // Keywords are ONLY for matching headings; we do NOT generate any new content.
    const groupKeywords = {
      "study": [
        "study", "education", "qualification", "pass", "8th", "10th", "12th",
        "iti", "diploma", "graduation", "graduate", "degree",
        "कक्षा", "पास", "योग्यता", "शिक्षा", "डिप्लोमा", "आईटीआई", "ग्रेजुएशन"
      ],
      "popular": [
        "popular", "category", "categories", "ssc", "railway", "police", "bank", "teaching",
        "लोकप्रिय", "कैटेगरी", "श्रेणी", "रेलवे", "पुलिस", "बैंक", "ssc"
      ],
      "state": [
        "state", "states", "wise", "state-wise", "राज्य", "स्टेट"
      ],
      "admissions": [
        "admission", "admissions", "apply", "registration", "counselling",
        "एडमिशन", "प्रवेश", "रजिस्ट्रेशन", "काउंसलिंग"
      ],
      "admit-result": [
        "admit", "admit card", "result", "answer key", "syllabus",
        "एडमिट", "रिजल्ट", "उत्तर कुंजी", "आंसर", "सिलेबस"
      ],
      "khabar": [
        "khabar", "news", "latest", "update", "updates",
        "खबर", "समाचार", "न्यूज़", "अपडेट"
      ],
      "study-material": [
        "study material", "material", "course", "courses", "notes", "pdf", "book",
        "स्टडी", "मटेरियल", "कोर्स", "नोट्स"
      ]
    };

    const wants = groupKeywords[group] || [];

    // First try: match by heading text
    let matched = nonEmptySections.filter(s => containsAny(s.heading, wants));

    // If nothing matched, fail gracefully but NEVER show a blank page:
    if(!matched.length){
      if(["study","popular","state"].includes(group)){
        matched = nonEmptySections.slice(0, 6);
      }else{
        matched = nonEmptySections.slice(0);
      }
    }

    const render = (blocksToRender, q="")=>{
      grid.classList.add("cat-grid");
      grid.innerHTML = "";

      if(!blocksToRender.length){
        if(empty) empty.style.display = "block";
        return;
      }
      if(empty) empty.style.display = "none";

      const colorMap={
        "study":"#2563eb",
        "popular":"#db2777",
        "state":"#059669",
        "admissions":"#f59e0b",
        "admit-result":"#ef4444",
        "khabar":"#7c3aed",
        "study-material":"#0ea5e9"
      };
      const color = colorMap[group] || "#0284c7";

      blocksToRender.forEach(b=>{
        const card = document.createElement("article");
        card.className = "section-card";
        card.innerHTML = `
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

        const list = $(".section-list", card);

        (b.items || []).forEach(x=>{
          const a = document.createElement("a");
          a.className = "section-link";

          const href = x.external ? normalizeUrl(x.url) : openInternal(x.url, x.name);
          a.href = href;
          if(x.external){ a.target="_blank"; a.rel="noopener"; }

          const qSafe = safe(q);
          const name = qSafe
            ? safe(x.name).replace(new RegExp(`(${escRE(qSafe)})`, "ig"), "<mark>$1</mark>")
            : safe(x.name);

          a.innerHTML = `
            <div class="t">${name}</div>
            <div class="d">Open official link</div>
          `;
          list.appendChild(a);
        });

        grid.appendChild(card);
      });

      renderCategorySEO(meta.title, meta.desc, group);
    };

    render(matched);

    if(filter){
      filter.addEventListener("input", ()=>{
        const q = safe(filter.value).toLowerCase();
        if(!q){ render(matched); return; }

        const filtered = matched
          .map(b=>({
            heading: b.heading,
            items: (b.items||[]).filter(x => safe(x.name).toLowerCase().includes(q))
          }))
          .filter(b => b.items.length);

        render(filtered, q);
      });
    }

    if(clear){
      clear.addEventListener("click", ()=>{
        if(!filter) return;
        filter.value = "";
        render(matched);
        filter.focus();
      });
    }
  }

  function renderCategorySEO(title, desc, group){
    // Minimal SEO injection without changing page structure:
    // - updates meta description
    // - adds simple FAQ snippet for category pages if container exists
    const m = document.querySelector('meta[name="description"]');
    if(m && safe(desc)) m.setAttribute("content", safe(desc));

    const faqWrap = $("#categoryFaq");
    if(!faqWrap) return;

    faqWrap.innerHTML = `
      <div class="faq-card">
        <h2>FAQs – ${safe(title)}</h2>
        <p class="faq-sub">${safe(desc)}</p>

        <div class="faq-item">
          <button type="button" class="faq-btn" aria-expanded="false">
            <span>Are these official links?</span>
            <i class="fas fa-chevron-down"></i>
          </button>
          <div class="faq-panel" hidden>
            We list official and trusted links. Always confirm dates and eligibility on the official portal.
          </div>
        </div>

        <div class="faq-item">
          <button type="button" class="faq-btn" aria-expanded="false">
            <span>Why do some links open in a viewer page?</span>
            <i class="fas fa-chevron-down"></i>
          </button>
          <div class="faq-panel" hidden>
            Internal viewer pages help keep navigation consistent. External links open directly.
          </div>
        </div>
      </div>
    `;

    initFAQ();
  }

  // -------------------------
  // CSC Services page (services.json)
  // -------------------------
  async function renderServicesPage(){
    if(page !== "govt-services.html") return;

    const list = $("#servicesList");
    if(!list) return;

    let data=null;
    try{
      const r=await fetch("services.json",{ cache:"no-store" });
      if(r.ok) data=await r.json();
    }catch(_){}

    const services=(data && (data.services||data)) || [];
    list.innerHTML="";

    if(!Array.isArray(services) || !services.length){
      list.innerHTML = `<div class="seo-block"><strong>No services found.</strong><p>Please check services.json.</p></div>`;
      return;
    }

    const wrap=document.createElement("div");
    wrap.className="section-card";
    wrap.innerHTML = `
      <div class="section-head" style="background:#0284c7">
        <div class="left">
          <i class="fa-solid fa-building-columns"></i>
          <span>Service Request</span>
        </div>
      </div>
      <div class="section-body">
        <div class="section-list" id="servicesInner"></div>
      </div>
    `;
    const inner=$("#servicesInner", wrap);

    services.forEach(s=>{
      const name=safe(s.name||s.service);
      const url=s.url||s.link||"";
      if(!name) return;

      const a=document.createElement("a");
      a.className="section-link";
      a.href = url ? normalizeUrl(url) : "#";
      if(url){
        a.target="_blank";
        a.rel="noopener";
      }
      a.innerHTML = `
        <div class="t">${name}</div>
        <div class="d">Open service</div>
      `;
      inner.appendChild(a);
    });

    list.appendChild(wrap);
  }

  // -------------------------
  // Tools page (tools.json)
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

    if(!data){
      grid.innerHTML = `<div class="seo-block"><strong>No tools found.</strong><p>Please check tools.json.</p></div>`;
      return;
    }

    const addGroup=(title, icon, arr)=>{
      if(!Array.isArray(arr) || !arr.length) return;

      const card=document.createElement("article");
      card.className="section-card";
      card.innerHTML = `
        <div class="section-head" style="background:#4f46e5">
          <div class="left">
            <i class="${icon}"></i>
            <span>${title}</span>
          </div>
        </div>
        <div class="section-body">
          <div class="section-list"></div>
        </div>
      `;
      const list=$(".section-list", card);

      arr.forEach(it=>{
        const name=safe(it.name)||"Open";
        const url=it.url||it.link||"";
        if(!url) return;

        const a=document.createElement("a");
        a.className="section-link";
        a.href = normalizeUrl(url);
        a.target="_blank";
        a.rel="noopener";
        a.innerHTML = `
          <div class="t">${name}</div>
          <div class="d">Open tool</div>
        `;
        list.appendChild(a);
      });

      grid.appendChild(card);
    };

    addGroup("PDF Tools", "fa-solid fa-file-pdf", data.pdf);
    addGroup("Image Tools", "fa-solid fa-image", data.image);
    addGroup("Video Tools", "fa-solid fa-video", data.video);

    const any = grid.children.length > 0;
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
              href: it.external ? normalizeUrl(url) : openInternal(url, title),
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
            href: it.external ? normalizeUrl(url) : openInternal(url, title),
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
              href: it.external ? normalizeUrl(url) : openInternal(url, title),
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
      const q = safe(input.value);
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
