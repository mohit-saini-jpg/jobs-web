#!/usr/bin/env python3
"""
patch_layout.py — Patches ALL existing static job pages (/jobs/*/index.html)
from the OLD layout (job-hero-card + job-card-head, no sidebar) to the
MODERN layout (jp-wrap + jp-three-col + Quick Highlights sidebar).

Run once after updating generate_jobs.py / generate_pages.py templates.
Usage: python3 scripts/patch_layout.py
"""

import os, re, sys

JOBS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jobs")

MODERN_CSS = """
    /* ══ Modern 3-Column Layout (jp-wrap) ══ */
    .jp-wrap { max-width: 1200px; margin: 0 auto; padding: 24px 12px 40px; }
    .jp-three-col { display: grid; grid-template-columns: 1fr 300px; gap: 20px; align-items: start; }
    @media (max-width: 900px) { .jp-three-col { grid-template-columns: 1fr; } }
    @media (max-width: 480px) { .jp-wrap { padding: 12px 8px max(32px, env(safe-area-inset-bottom, 32px)); } }
    .jp-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; border-top: 1px solid #e2e8f0; margin-top: 14px; }
    @media (max-width: 640px) { .jp-stats { grid-template-columns: repeat(2, 1fr); } }
    .jp-stat { text-align: center; padding: 12px 8px; border-right: 1px solid #e2e8f0; }
    .jp-stat:last-child { border-right: none; }
    .jp-stat-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 4px; }
    .jp-stat-value { font-size: 14px; font-weight: 700; color: #0f172a; }
    .jp-stat-value.green { color: #16a34a; }
    .jp-stat-value.blue  { color: #2563eb; }
    .jp-sidebar { display: flex; flex-direction: column; gap: 14px; }
    .jp-sidebar-card { background: #fff; border-radius: 12px; border: 1.5px solid #e2e8f0; overflow: hidden; }
    .jp-sidebar-card-head { background: linear-gradient(135deg,#dc2626,#b91c1c); color: #fff; padding: 10px 14px; font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 7px; }
    .jp-sidebar-card-body { padding: 12px 14px; }
    .jp-hl-list { list-style: none; margin: 0; padding: 0; }
    .jp-hl-list li { display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 12.5px; color: #374151; }
    .jp-hl-list li:last-child { border-bottom: none; }
    .jp-hl-list li i { color: #16a34a; margin-top: 2px; flex-shrink: 0; font-size: 12px; }
    .jp-share-card-head { background: linear-gradient(135deg,#7c3aed,#6d28d9); color: #fff; padding: 10px 14px; font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 7px; }
    .jp-share-btns { display: flex; flex-direction: column; gap: 8px; padding: 12px 14px; }
    .jp-share-btn { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 7px; font-size: 13px; font-weight: 600; text-decoration: none; color: #fff; cursor: pointer; border: none; transition: opacity .2s; }
    .jp-share-btn:hover { opacity: .88; }
    .jp-share-btn.wa { background: #25D366; }
    .jp-share-btn.tg { background: #229ED9; }
    .jp-share-btn.fb { background: #1877F2; }
    .jp-share-btn.cp { background: #475569; }"""

def extract_meta(html, name):
    m = re.search(rf'<meta\s+name=["\']?{name}["\']?\s+content=["\']([^"\']*)["\']', html)
    if not m:
        m = re.search(rf'<meta\s+content=["\']([^"\']*)["\'][^>]*name=["\']?{name}["\']', html)
    return m.group(1) if m else ""

def extract_og(html, prop):
    m = re.search(rf'<meta\s+property=["\']og:{prop}["\']\s+content=["\']([^"\']*)["\']', html)
    if not m:
        m = re.search(rf'content=["\']([^"\']*)["\'][^>]*property=["\']og:{prop}["\']', html)
    return m.group(1) if m else ""

def extract_jp_stat(html, label_text):
    """Pull value from existing jp-stat blocks if already patched."""
    m = re.search(rf'jp-stat-label[^>]*>\s*{label_text}\s*</div>\s*<div[^>]*jp-stat-value[^>]*>([^<]*)</div', html, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def extract_badge(html, badge_class):
    m = re.search(rf'<span class=["\']badge {badge_class}["\'][^>]*>.*?(?:Posts:|Last Date:|</i>)\s*([^<]+)', html)
    return m.group(1).strip() if m else ""

def extract_hl_item(html, label):
    """Extract from Quick Highlights sidebar if exists."""
    m = re.search(rf'<strong>{label}:</strong>\s*([^<]+)', html)
    return m.group(1).strip() if m else ""

def extract_canonical(html):
    m = re.search(r'<link\s+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html)
    return m.group(1) if m else ""

def extract_slug(html):
    m = re.search(r'window\.__TSJ_SLUG\s*=\s*["\']([^"\']+)["\']', html)
    return m.group(1) if m else ""

def extract_hero_data(html):
    """Extract org, posts, last_date, mode from the old hero badge area."""
    org = ""
    posts = "Various"
    last_date = "See Notification"
    mode = "Online"

    # Try from jp-hl-list (if partially patched)
    org_m = extract_hl_item(html, "Organisation")
    if org_m and org_m != "See Notification": org = org_m

    posts_m = extract_hl_item(html, "Total Posts")
    if posts_m and posts_m != "Various": posts = posts_m

    ld_m = extract_hl_item(html, "Last Date")
    if ld_m and ld_m != "See Notification": last_date = ld_m

    mode_m = extract_hl_item(html, "Apply Mode")
    if mode_m and mode_m != "Online": mode = mode_m

    # Fallback: old badge spans
    if not org:
        m = re.search(r'<span[^>]*itemprop=["\']name["\'][^>]*>([^<]+)<', html)
        if m: org = m.group(1).strip()
    if not org:
        m = re.search(r'class=["\']job-org["\'][^>]*>\s*<span[^>]*>([^<]+)<', html)
        if m: org = m.group(1).strip()

    if posts == "Various":
        m = re.search(r'badge-posts["\'][^>]*>.*?Posts:\s*([^<]+)<', html)
        if m: posts = m.group(1).strip()
        if posts == "Various":
            m2 = re.search(r'"totalJobOpenings"\s*:\s*(\d+)', html)
            if m2: posts = m2.group(1)

    if last_date == "See Notification":
        m = re.search(r'badge-date["\'][^>]*>.*?Last Date:\s*([^<]+)<', html)
        if m: last_date = m.group(1).strip()

    if mode == "Online":
        m = re.search(r'badge-mode["\'][^>]*>.*?</i>\s*([^<]+)<', html)
        if m: mode = m.group(1).strip()

    return org.strip(), posts.strip(), last_date.strip(), mode.strip()

def extract_apply_url(html):
    """Find a good apply URL from important links section."""
    for pat in [
        r'btn-green["\'][^>]+href=["\']([^"\']+)["\']',
        r'href=["\']([^"\']+)["\'][^>]+btn-green',
        r'Apply Online.*?href=["\']([^"\']+)["\']',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m and m.group(1).startswith("http"):
            return m.group(1)
    return ""

def already_patched(html):
    return "jp-three-col" in html and "jp-sidebar" in html

def inject_css(html):
    """Inject modern CSS into <style> block or before </head>."""
    if "jp-wrap" in html:
        return html  # already has CSS
    # Find existing <style> block end
    style_end = html.rfind("</style>")
    if style_end != -1:
        return html[:style_end] + MODERN_CSS + "\n  " + html[style_end:]
    # Fallback: before </head>
    head_end = html.find("</head>")
    if head_end != -1:
        css_tag = f"<style>{MODERN_CSS}\n</style>\n"
        return html[:head_end] + css_tag + html[head_end:]
    return html

def build_sidebar(org, posts, last_date, mode, canonical, apply_url):
    encoded_title = ""  # share without title to keep it simple
    return f"""
      <!-- RIGHT: sidebar -->
      <aside class="jp-sidebar">
        <div class="jp-sidebar-card">
          <div class="jp-sidebar-card-head"><i class="fa-solid fa-star"></i> Quick Highlights</div>
          <div class="jp-sidebar-card-body">
            <ul class="jp-hl-list">
              <li><i class="fa-solid fa-circle-check"></i> <div><strong>Organisation:</strong> {org if org else "See Notification"}</div></li>
              <li><i class="fa-solid fa-circle-check"></i> <div><strong>Total Posts:</strong> {posts}</div></li>
              <li><i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b"></i> <div><strong>Last Date:</strong> {last_date}</div></li>
              <li><i class="fa-solid fa-circle-check"></i> <div><strong>Apply Mode:</strong> {mode}</div></li>
            </ul>
          </div>
        </div>
        <div class="jp-sidebar-card">
          <div class="jp-share-card-head"><i class="fa-solid fa-share-nodes"></i> Share This Job</div>
          <div class="jp-share-btns">
            <a class="jp-share-btn wa" href="https://wa.me/?text={canonical}" target="_blank" rel="noopener"><i class="fa-brands fa-whatsapp"></i> WhatsApp</a>
            <a class="jp-share-btn tg" href="https://t.me/share/url?url={canonical}" target="_blank" rel="noopener"><i class="fa-brands fa-telegram"></i> Telegram</a>
            <a class="jp-share-btn fb" href="https://www.facebook.com/sharer/sharer.php?u={canonical}" target="_blank" rel="noopener"><i class="fa-brands fa-facebook-f"></i> Facebook</a>
            <button class="jp-share-btn cp" onclick="navigator.clipboard.writeText('{canonical}').then(function(){{var t=this;this.textContent='✅ Copied!';setTimeout(function(){{t.textContent='🔗 Copy Link'}},2000)}}.bind(this))"><i class="fa-solid fa-link"></i> Copy Link</button>
          </div>
        </div>
        {"<div class='jp-sidebar-card'><div class='jp-sidebar-card-head' style='background:linear-gradient(135deg,#0369a1,#0284c7)'><i class='fa-solid fa-calendar-days'></i> Important Dates</div><div class='jp-sidebar-card-body'><ul class='jp-hl-list'><li><i class='fa-solid fa-calendar-check' style='color:#0369a1'></i><div><strong>Last Date:</strong> " + last_date + "</div></li></ul></div></div>" if last_date and last_date != "See Notification" else ""}
        {"<a href='" + apply_url + "' target='_blank' rel='noopener noreferrer' style='display:flex;align-items:center;justify-content:center;gap:8px;padding:14px;border-radius:10px;font-size:15px;font-weight:700;text-decoration:none;color:#fff;background:linear-gradient(135deg,#059669,#047857);'><i class='fa-solid fa-arrow-up-right-from-square'></i> Apply Online / Official Website</a>" if apply_url else ""}
      </aside>"""

def build_stats_bar(org, posts, last_date, mode):
    return f"""<div class="jp-stats">
              <div class="jp-stat"><div class="jp-stat-label">Organisation</div><div class="jp-stat-value">{org if org else "—"}</div></div>
              <div class="jp-stat"><div class="jp-stat-label">Total Posts</div><div class="jp-stat-value blue">{posts}</div></div>
              <div class="jp-stat"><div class="jp-stat-label">Last Date</div><div class="jp-stat-value" style="color:#dc2626">{last_date}</div></div>
              <div class="jp-stat"><div class="jp-stat-label">Apply Mode</div><div class="jp-stat-value green">{mode}</div></div>
            </div>"""

def patch_html(html, path):
    if already_patched(html):
        return html, False  # skip

    # 1. Inject CSS
    html = inject_css(html)

    # 2. Extract data
    canonical = extract_canonical(html)
    org, posts, last_date, mode = extract_hero_data(html)
    apply_url = extract_apply_url(html)
    slug = extract_slug(html)

    # 3. Replace old <div class="container"> wrapper with jp-wrap
    # Pattern: <main id="main-content">\n  <div class="container">
    html = re.sub(
        r'<main id=["\']main-content["\']>\s*<div class=["\']container["\']>',
        '<main id="main-content">\n  <div class="jp-wrap">\n    <div class="jp-three-col">',
        html
    )

    # 4. Replace old breadcrumb (no change needed, just wrap in main col div)
    # Insert <div class="jp-main-col"> after jp-three-col opening
    html = re.sub(
        r'(<div class=["\']jp-three-col["\']>)\s*(<nav class=["\']breadcrumb["\'])',
        r'\1\n      <div class="jp-main-col">\n        \2',
        html
    )

    # 5. Replace old badge row with jp-stats inside hero header
    # Pattern: <div class="job-badges">.....</div>
    stats_bar = build_stats_bar(org, posts, last_date, mode)
    html = re.sub(
        r'<div class=["\']job-badges["\']>.*?</div>',
        stats_bar,
        html,
        count=1,
        flags=re.DOTALL
    )

    # 6. Close </article> and then close jp-main-col, add sidebar, close jp-three-col
    sidebar_html = build_sidebar(org, posts, last_date, mode, canonical, apply_url)

    # Find </article> and close everything after it
    html = re.sub(
        r'</article>\s*</div>\s*</main>',
        f'</article>\n      </div><!-- /jp-main-col -->{sidebar_html}\n    </div><!-- /jp-three-col -->\n  </div><!-- /jp-wrap -->\n</main>',
        html,
        count=1,
        flags=re.DOTALL
    )

    # 7. Add pwa-install.js + tsj-push.js if missing
    if "pwa-install.js" not in html:
        html = html.replace(
            '<script src="/tsj-menu.js" defer></script>',
            '<script src="/tsj-menu.js" defer></script>\n<script src="/pwa-install.js?v=6.0" defer></script>\n<script src="/tsj-push.js"></script>'
        )

    return html, True

def main():
    if not os.path.isdir(JOBS_DIR):
        print(f"ERROR: jobs dir not found: {JOBS_DIR}")
        sys.exit(1)

    total = 0
    patched = 0
    skipped = 0
    errors = 0

    folders = [d for d in os.listdir(JOBS_DIR)
               if os.path.isdir(os.path.join(JOBS_DIR, d)) and d != "data"]
    total = len(folders)
    print(f"Found {total} job folders. Patching...")

    for i, folder in enumerate(folders):
        idx_path = os.path.join(JOBS_DIR, folder, "index.html")
        if not os.path.exists(idx_path):
            skipped += 1
            continue
        try:
            with open(idx_path, encoding="utf-8") as f:
                html = f.read()
            new_html, changed = patch_html(html, idx_path)
            if changed:
                with open(idx_path, "w", encoding="utf-8") as f:
                    f.write(new_html)
                patched += 1
            else:
                skipped += 1
        except Exception as ex:
            errors += 1
            if errors <= 5:
                print(f"  ERROR: {folder}: {ex}")

        if (i + 1) % 500 == 0:
            print(f"  ... {i+1}/{total} processed ({patched} patched, {skipped} skipped, {errors} errors)")

    print(f"\n✅ Done! {patched} pages patched, {skipped} skipped (already modern), {errors} errors.")

if __name__ == "__main__":
    main()
