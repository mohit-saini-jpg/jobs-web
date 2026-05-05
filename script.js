(data.sections || []).forEach((sec) => {
  const title = safe(sec.title) || "Updates";
  const baseColor = safe(sec.color) || "#0284c7";
  const icon = safe(sec.icon) || "fa-solid fa-briefcase";

  const bgStyle = baseColor.includes("gradient") 
    ? `background: ${baseColor};` 
    : `background-color: ${baseColor}; background-image: linear-gradient(135deg, rgba(255,255,255,0.18) 0%, rgba(0,0,0,0.15) 100%);`;

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
    <div class="section-head" style="${bgStyle}">
      <div class="left">
        <i class="${icon}"></i>
        <span>${title}</span>
      </div>
    </div>
    <div class="section-body">
      <div class="section-list"></div>
      ${moreHref ? `<a class="view-all" href="${moreHref}">More</a>` : ""}
    </div>
  `;

  const list = $(".section-list", card);

  const items = Array.isArray(sec.items)
    ? sec.items.slice(0, 8)
    : [];

  items.forEach((it) => {
    const name = safe(it.name) || "Open";

    const a = document.createElement("a");
    a.className = "section-link";

    // ✅ SEO friendly link (redirect removed)
    const slug = slugifyTitle(name);
    a.href = `view.html?job=${slug}`;

    a.innerHTML = `<div class="t">${name}</div>`;
    list.appendChild(a);
  });

  // ✅ Show More (single clean block)
  if (items.length > 4) {
    const btn = document.createElement("button");
    btn.className = "section-show-more";
    btn.textContent = "Show all " + items.length;

    btn.onclick = () => {
      list.querySelectorAll('[data-collapsed="1"]').forEach(el => el.removeAttribute("data-collapsed"));
      btn.remove();
    };

    card.appendChild(btn);
  }

  wrap.appendChild(card);

}); // ✅ loop properly closed
