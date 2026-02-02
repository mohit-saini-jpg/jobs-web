(function () {
  "use strict";

  // ---------- helpers ----------
  const $ = (id) => document.getElementById(id);

  function isExternal(url) {
    return /^https?:\/\//i.test(url);
  }

  function safeText(str) {
    return (str || "").toString().trim();
  }

  function makeBtn({ text, href, bg, external = false, iconClass = "" }) {
    const a = document.createElement("a");
    a.href = href || "#";
    a.className =
      "inline-flex items-center justify-center gap-2 rounded-xl font-semibold shadow-sm hover:shadow-md transition " +
      "px-4 py-3 text-white text-sm md:text-base";
    a.style.background = bg || "#0ea5e9";
    a.style.maxWidth = "100%";
    a.style.textAlign = "center";
    a.style.lineHeight = "1.2";
    a.style.whiteSpace = "normal";
    a.style.wordBreak = "break-word";
    a.style.overflowWrap = "anywhere";

    if (external || isExternal(a.href)) {
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }

    if (iconClass) {
      const i = document.createElement("i");
      i.className = iconClass;
      a.appendChild(i);
    }

    const span = document.createElement("span");
    span.textContent = safeText(text);
    a.appendChild(span);
    return a;
  }

  function makeChip({ text, href, bg, external = false }) {
    const a = document.createElement("a");
    a.href = href || "#";
    a.className =
      "inline-flex items-center justify-center rounded-full font-bold shadow hover:shadow-lg transition " +
      "px-5 py-3 text-white text-base";
    a.style.background = bg || "#14b8a6";
    a.style.maxWidth = "100%";
    a.style.textAlign = "center";
    a.style.lineHeight = "1.2";
    a.style.whiteSpace = "normal";
    a.style.wordBreak = "break-word";
    a.style.overflowWrap = "anywhere";

    if (external || isExternal(a.href)) {
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }
    a.textContent = safeText(text);
    return a;
  }

  function makeSectionTitle(text, color) {
    const div = document.createElement("div");
    div.className =
      "col-span-full rounded-lg px-4 py-2 font-extrabold text-white shadow-sm";
    div.style.background = color || "#60a5fa";
    div.style.lineHeight = "1.2";
    div.style.whiteSpace = "normal";
    div.style.wordBreak = "break-word";
    div.style.overflowWrap = "anywhere";
    div.textContent = safeText(text);
    return div;
  }

  // ---------- header overflow fix ----------
  function fixHeaderOverflow() {
    // Make desktop nav horizontally scrollable so it never cuts off.
    const header = document.querySelector("header");
    if (!header) return;

    const nav = header.querySelector("nav.hidden.lg\\:flex");
    if (nav) {
      nav.style.flex = "1";
      nav.style.minWidth = "0";
      nav.style.overflowX = "auto";
      nav.style.whiteSpace = "nowrap";
      nav.style.scrollbarWidth = "thin";
      nav.style.paddingBottom = "2px";
    }

    // Ensure title/logo doesn't shrink weirdly
    const h1 = header.querySelector("h1");
    if (h1) h1.style.flexShrink = "0";
  }

  // ---------- mobile menu toggle (safe) ----------
  function setupMobileMenuToggle() {
    const toggleBtn = $("mobile-menu-toggle");
    const mobileMenu = $("mobile-menu");
    if (!toggleBtn || !mobileMenu) return;

    toggleBtn.addEventListener("click", () => {
      mobileMenu.classList.toggle("hidden");
    });

    // close on link click
    mobileMenu.addEventListener("click", (e) => {
      const t = e.target;
      if (t && t.closest && t.closest("a")) {
        mobileMenu.classList.add("hidden");
      }
    });
  }

  // ---------- optional utility links (right side in header) ----------
  // NOTE: These do NOT affect your main nav. They only render inside #header-links and #header-links-mobile.
  const utilityLinks = [
    {
      text: "AI Helpdesk",
      href: "helpdesk.html",
      bg: "#ef4444",
      iconClass: "fas fa-robot",
      external: false
    },
    {
      text: "Resume/CV Maker",
      href: "tools.html",
      bg: "#6b7280",
      iconClass: "fas fa-file-lines",
      external: false
    },
    {
      text: "Join WhatsApp",
      href: "https://wa.me/",
      bg: "#16a34a",
      iconClass: "fab fa-whatsapp",
      external: true
    }
  ];

  function renderUtilityLinks() {
    const desktop = $("header-links");
    const mobile = $("header-links-mobile");
    if (desktop) desktop.innerHTML = "";
    if (mobile) mobile.innerHTML = "";

    utilityLinks.forEach((l) => {
      const btn = makeBtn(l);
      btn.className += " rounded-2xl"; // match your existing look

      if (desktop) {
        desktop.appendChild(btn);
      }
      if (mobile) {
        const wrap = document.createElement("div");
        wrap.appendChild(btn);
        mobile.appendChild(wrap);
      }
    });
  }

  // ---------- footer social links (optional) ----------
  const footerSocial = [
    // Put your real links here if you want
    // { text: "Telegram", href: "https://t.me/yourchannel", iconClass: "fab fa-telegram", bg: "#229ED9" },
  ];

  function renderFooterSocial() {
    const el = $("footer-social-links");
    if (!el) return;
    el.innerHTML = "";

    footerSocial.forEach((s) => {
      const a = makeBtn({
        text: s.text,
        href: s.href,
        bg: s.bg || "#0ea5e9",
        iconClass: s.iconClass || "",
        external: true
      });
      a.className =
        "inline-flex items-center gap-2 px-4 py-2 rounded-full text-white font-semibold shadow hover:shadow-md transition";
      el.appendChild(a);
    });
  }

  // ---------- jobs.json rendering ----------
  async function loadJobs() {
    // tries jobs.json at root
    const res = await fetch("jobs.json", { cache: "no-store" });
    if (!res.ok) throw new Error("jobs.json not found or cannot be loaded");
    return await res.json();
  }

  function renderHomeSection(topJobs) {
    const home = $("home-section");
    if (!home) return;
    home.innerHTML = "";
    home.classList.add("flex", "flex-wrap", "gap-3");

    let currentColor = "#14b8a6";

    topJobs.forEach((item) => {
      // section heading object: {title,color}
      if (item && item.title) {
        currentColor = item.color || currentColor;
        const titleChip = document.createElement("div");
        titleChip.className =
          "px-4 py-2 rounded-full font-extrabold text-white shadow";
        titleChip.style.background = currentColor;
        titleChip.style.maxWidth = "100%";
        titleChip.style.whiteSpace = "normal";
        titleChip.style.wordBreak = "break-word";
        titleChip.style.overflowWrap = "anywhere";
        titleChip.textContent = safeText(item.title);
        home.appendChild(titleChip);
        return;
      }

      // job link object: {name,url,external}
      if (item && item.name && item.url) {
        const chip = makeChip({
          text: item.name,
          href: item.url,
          bg: item.color || currentColor,
          external: !!item.external
        });
        home.appendChild(chip);
      }
    });
  }

  function renderSidebar(list, containerId) {
    const el = $(containerId);
    if (!el) return;
    el.innerHTML = "";

    // preserve your layout: grid grid-cols-2
    el.classList.add("gap-2");

    let currentColor = "#0ea5e9";

    list.forEach((item) => {
      if (item && item.title) {
        currentColor = item.color || currentColor;

        // put section title spanning both columns
        const title = makeSectionTitle(item.title, currentColor);
        el.appendChild(title);
        return;
      }

      if (item && item.name && item.url) {
        const a = document.createElement("a");
        a.href = item.url;
        a.className =
          "rounded-lg px-3 py-3 font-bold text-white shadow hover:shadow-md transition text-center";
        a.style.background = item.color || currentColor;
        a.style.lineHeight = "1.2";
        a.style.whiteSpace = "normal";
        a.style.wordBreak = "break-word";
        a.style.overflowWrap = "anywhere";
        a.style.display = "flex";
        a.style.alignItems = "center";
        a.style.justifyContent = "center";
        a.style.minHeight = "44px";

        if (item.external || isExternal(item.url)) {
          a.target = "_blank";
          a.rel = "noopener noreferrer";
        }

        a.textContent = safeText(item.name);
        el.appendChild(a);
      }
    });
  }

  // ---------- init ----------
  async function init() {
    fixHeaderOverflow();
    setupMobileMenuToggle();

    // This will NOT remove your About/Contact/Privacy/Terms etc.
    // It only fills the utility containers.
    renderUtilityLinks();
    renderFooterSocial();

    // Load jobs.json and render chips + sidebars
    try {
      const data = await loadJobs();
      if (data && Array.isArray(data.top_jobs)) renderHomeSection(data.top_jobs);
      if (data && Array.isArray(data.left_jobs)) renderSidebar(data.left_jobs, "jobs-left-section");
      if (data && Array.isArray(data.right_jobs)) renderSidebar(data.right_jobs, "jobs-right-section");
    } catch (e) {
      // If jobs.json fails, do nothing (site still works)
      console.warn("Jobs rendering skipped:", e.message);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
