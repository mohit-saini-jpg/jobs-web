#!/usr/bin/env python3
"""
patch_ai_html.py — TSJ AI HTML Patcher
======================================
Existing built HTML files mein AI sections directly inject karta hai.
generate_all.py chalane ki zaroorat nahi.

Usage:
  python3 patch_ai_html.py
  python3 patch_ai_html.py --dry-run   # sirf count, kuch likhega nahi
  python3 patch_ai_html.py --slug bpssc-company-commander-...  # single page test

What it does:
  1. Complete_Jobs_Full_Data.json se AI data wale jobs load karta hai
  2. Har job ka /jobs/<slug>/index.html find karta hai
  3. Agar page mein AI sections nahi hain → inject karta hai
  4. Title tag + meta description bhi update karta hai (ai_title/ai_meta_description)
  5. FAQ section bhi update karta hai (ai_expanded_faqs)
"""

import json, re, os, sys, html as _html
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
DATA_FILE = Path(os.environ.get("AI_DATA_FILE", "Complete_Jobs_Full_Data.json"))
JOBS_DIR  = Path("jobs")          # output /jobs/<slug>/index.html
DRY_RUN   = "--dry-run" in sys.argv
SINGLE    = None
for i, a in enumerate(sys.argv):
    if a == "--slug" and i+1 < len(sys.argv):
        SINGLE = sys.argv[i+1]

# ── Helpers ───────────────────────────────────────────────────────────────────
def e(s):
    return _html.escape(str(s or ""), quote=True)

def safe(v, maxlen=0):
    if v is None: return ""
    s = str(v).strip()
    return s[:maxlen] if maxlen else s

def brand_help_faq(job_obj):
    """Same as generate_all.brand_help_faq() — ek brand-attributed, category-tailored,
    page-specific Q&A. AI-patch flow me bhi add hota hai taaki har page pe branded
    Q&A rahe (sentinel replace ke baad bhi survive kare). Truthful + page-specific."""
    if not isinstance(job_obj, dict):
        return None
    bd = job_obj.get('basic_details') or {}
    title = safe(bd.get('job_title', '') or job_obj.get('title', '')
                 or job_obj.get('post_name', '') or 'this notification')
    if not title:
        return None
    cat = (job_obj.get('category', '') or '').upper()
    tl = title.lower()

    def hit(*words):
        return any(w in cat or w in tl for w in words)

    SITE = "www.topsarkarijobs.com"
    if hit('ANSWER', 'answer key'):
        q = f"Where can I download the official Answer Key for {title}?"
        a = (f"Ans: The official answer key and question-paper solutions for {title} "
             f"can be downloaded through the verified link listed on {SITE}.")
    elif hit('ADMIT', 'admit card', 'hall ticket', 'call letter'):
        q = f"How can I download the Admit Card for {title}?"
        a = (f"Ans: The admit card / hall ticket for {title} can be downloaded from "
             f"the official portal using the direct link provided on {SITE}.")
    elif hit('RESULT', 'merit list', 'score card', 'cut off', 'cutoff'):
        q = f"How can I check the result for {title}?"
        a = (f"Ans: You can check the marks, merit list and cut-off for {title} "
             f"through the official result link provided on {SITE}.")
    elif hit('ADMISSION', 'SYLLABUS', 'YOJANA', 'SCHEME', 'SCHOLARSHIP',
             'syllabus', 'admission', 'yojana', 'scheme', 'scholarship'):
        q = f"Where can I get the latest official updates for {title}?"
        a = (f"Ans: All official PDFs, notifications and step-by-step guides for "
             f"{title} are available on {SITE}.")
    else:
        q = f"How can I apply for {title}?"
        a = (f"Ans: You can apply online through the official recruitment link "
             f"provided for {title} on {SITE}. Read the full notification and check "
             f"your eligibility before applying on the official portal.")
    a += (" TopSarkariJobs began compiling verified government-job updates in 2020 "
          "and launched online in 2025.")
    return {"question": q, "answer": a}

def sec_card(heading, icon, grad, body):
    """Exact same HTML as generate_all.py sec_card() (2026 facts-first
    redesign: 'lightBgHex,#accentHex' calm tint, not a saturated gradient).
    <h2> stays attribute-free — generate_all.py's dedup/pairing regexes match
    a bare `<h2>...</h2>`."""
    _bg, _sep, _accent = grad.partition(',')
    _bg = _bg if _bg.startswith('#') else f'#{_bg}'
    _accent = _accent or '#4a5578'
    return (
        f'<section class="sec-card">'
        f'<div class="sec-head" style="background:{_bg};border-left:4px solid {_accent}">'
        f'<i class="fa-solid {icon}" style="color:{_accent}"></i><h2>{e(heading)}</h2></div>'
        f'<div class="sec-body">{body}</div></section>\n'
    )

def render_ai_sections(job):
    """Same as generate_all._render_ai_sections(): consolidate every AI
    commentary field into ONE accordion card ('More About This
    Recruitment') instead of one full-width sec_card per topic."""
    ai_cards = [
        ("ai_overview",             "Overview",           "fa-circle-info",        "eef3fc,#2452c4"),
        ("ai_expert_analysis",      "Expert Analysis",    "fa-lightbulb",          "f1eefc,#5b3fa0"),
        ("ai_who_should_apply",     "Who Should Apply",   "fa-user-check",         "eaf6f4,#0f766e"),
        ("ai_preparation_tips",     "Preparation Tips",   "fa-list-check",         "eaf7ef,#15803d"),
        ("ai_salary_insights",      "Salary Insights",    "fa-indian-rupee-sign",  "fceef1,#9d2449"),
        ("ai_job_profile_analysis", "Job Profile",        "fa-briefcase",          "f3f4f8,#4a5578"),
        ("ai_selection_strategy",   "Selection Strategy", "fa-bullseye",           "fcf3e7,#b4650a"),
    ]
    items = ""
    for key, heading, icon, _color in ai_cards:
        val = safe(job.get(key) or "")
        if val and len(val) > 20:
            _open = " open" if not items else ""
            items += (f'<details class="ai-item"{_open}><summary><i class="fa-solid {icon}"></i> {e(heading)}'
                      f'<i class="fa-solid fa-chevron-down ai-chev" aria-hidden="true"></i></summary>'
                      f'<div class="ai-item-body">{e(val)}</div></details>')
    if not items:
        return ""
    return sec_card("More About This Recruitment", "fa-wand-magic-sparkles", "f7f7fa,#6b7488",
                     f'<div class="ai-acc">{items}</div>')

def render_faq(faq_list):
    """Same as generate_all.render_faq()"""
    if not isinstance(faq_list, list) or not faq_list:
        return ""
    items = ""
    seen  = set()
    idx   = 0
    for f in faq_list:
        if not isinstance(f, dict): continue
        q = safe(f.get("question", ""))
        a = safe(f.get("answer", ""))
        if not q or not a: continue
        def _looks_q(s):
            sl = s.strip().lower()
            return sl.endswith("?") or bool(re.match(
                r"^(what|when|how|who|where|which|is|are|can|will|does|do|whom|whose|why)\b", sl))
        if _looks_q(a) and not _looks_q(q):
            q, a = a, q
        q = re.sub(r"^\s*Q?\s*\d{1,3}\s*[\.\):\-]\s*", "", q, flags=re.I).strip()
        key = re.sub(r"\s+", " ", q.lower()).strip()
        if not key or key in seen: continue
        seen.add(key)
        idx += 1
        _op = " open" if idx == 1 else ""
        items += (
            f'<div class="faq-item" id="faq-{idx}">'
            f'<div class="faq-q{_op}"><span class="faq-icon">Q{idx}</span>'
            f'<span class="faq-q-text">{e(q)}</span>'
            f'<i class="fa-solid fa-chevron-down faq-chev" aria-hidden="true"></i></div>'
            f'<div class="faq-a{_op}"><span class="faq-a-icon faq-icon" style="background:#15803d">A</span>'
            f'<div>{e(a)}</div></div></div>'
        )
    return items

def get_slug(job):
    return (job.get("_canonical_slug") or job.get("slug") or "").strip()

# ── Sentinel markers (idempotent re-inject) ───────────────────────────────────
_AI_BLOCK_START = '<!-- TSJ_AI_BLOCK_START -->'
_AI_BLOCK_END   = '<!-- TSJ_AI_BLOCK_END -->'
_AI_FAQ_START   = '<!-- TSJ_AI_FAQ_START -->'
_AI_FAQ_END     = '<!-- TSJ_AI_FAQ_END -->'

# ── Main patcher ──────────────────────────────────────────────────────────────
def patch_html(html: str, job: dict) -> tuple[str, list]:
    """
    Existing HTML mein AI data inject karo.
    Returns (new_html, list_of_changes_made)
    """
    changes = []

    # ── 1. AI sections inject ────────────────────────────────────────────────
    ai_html = render_ai_sections(job)
    if ai_html:
        wrapped_ai = f'{_AI_BLOCK_START}\n{ai_html}{_AI_BLOCK_END}\n'
        if _AI_BLOCK_START in html:
            # Sentinel present → replace the entire existing block
            html = re.sub(
                re.escape(_AI_BLOCK_START) + r'.*?' + re.escape(_AI_BLOCK_END) + r'\n?',
                wrapped_ai,
                html, count=1, flags=re.DOTALL
            )
            changes.append(f"replaced AI block ({ai_html.count('sec-card')} section(s))")
        else:
            # First injection: facts-first (2026) — insert just before the
            # base page's own FAQ section, not the first sec-card, so
            # commentary never buries Important Dates/Fee/Eligibility.
            _faq_m = re.search(
                r'<(?:div|section) class="sec-card">(?:(?!<(?:div|section) class="sec-card">).)*?faq-(?:item|q-text)',
                html, re.S)
            # _faq_m.start() IS the FAQ card's own opening tag position (the
            # pattern is anchored there) — do NOT rfind() an "earlier"
            # sec-card, that lands before the PRECEDING card (off-by-one).
            pos = _faq_m.start() if _faq_m else html.find('<section class="sec-card">')
            if pos != -1:
                html = html[:pos] + wrapped_ai + html[pos:]
                changes.append(f"injected {ai_html.count('sec-card')} AI section(s)")
            else:
                for end_tag in ["</main>", "</article>", "</body>"]:
                    pos = html.rfind(end_tag)
                    if pos != -1:
                        html = html[:pos] + wrapped_ai + html[pos:]
                        changes.append(f"injected {ai_html.count('sec-card')} AI section(s) (fallback)")
                        break

    # ── 2. Title tag update ──────────────────────────────────────────────────
    ai_title = safe(job.get("ai_title") or "")
    if ai_title:
        new_title = ai_title[:65].rstrip()
        new_html, n = re.subn(
            r'(<title>)(.*?)(</title>)',
            lambda m: m.group(1) + e(new_title) + m.group(3),
            html, count=1, flags=re.DOTALL
        )
        if n:
            html = new_html
            changes.append("updated <title>")

    # ── 3. Meta description update ───────────────────────────────────────────
    ai_meta = safe(job.get("ai_meta_description") or "")
    if ai_meta:
        new_meta = ai_meta[:160].rstrip()
        new_html, n = re.subn(
            r'(<meta\s+name=["\']description["\']\s+content=["\'])([^"\']*?)(["\'])',
            lambda m: m.group(1) + e(new_meta) + m.group(3),
            html, count=1, flags=re.IGNORECASE
        )
        if n:
            html = new_html
            changes.append("updated meta description")

    # ── 4. H1 update ─────────────────────────────────────────────────────────
    ai_h1 = safe(job.get("ai_h1") or "")
    if ai_h1:
        new_html, n = re.subn(
            r'(<h1[^>]*class="[^"]*post-title[^"]*"[^>]*>)(.*?)(</h1>)',
            lambda m: m.group(1) + e(ai_h1) + m.group(3),
            html, count=1, flags=re.DOTALL | re.IGNORECASE
        )
        if n:
            html = new_html
            changes.append("updated h1")

    # ── 5. FAQ section update ─────────────────────────────────────────────────
    ai_faqs = job.get("ai_expanded_faqs") or []
    # BRAND: branded category-tailored Q&A yahan bhi add karo, warna sentinel
    # replace hone pe wo gir jaata (generate_all.py se consistent rahe).
    _brand_qa = brand_help_faq(job)
    if isinstance(ai_faqs, list):
        ai_faqs = list(ai_faqs)
        if _brand_qa and _brand_qa not in ai_faqs:
            ai_faqs.append(_brand_qa)
    if isinstance(ai_faqs, list) and ai_faqs:
        faq_html = render_faq(ai_faqs)
        if faq_html:
            wrapped_faq = f'{_AI_FAQ_START}{faq_html}{_AI_FAQ_END}'
            if _AI_FAQ_START in html:
                # Sentinel present → replace existing FAQ block
                html = re.sub(
                    re.escape(_AI_FAQ_START) + r'.*?' + re.escape(_AI_FAQ_END),
                    wrapped_faq,
                    html, count=1, flags=re.DOTALL
                )
                changes.append("replaced FAQ block")
            else:
                # First injection: insert items inside .faq-wrap
                faq_pat = re.compile(
                    r'(<div[^>]+class="[^"]*faq-wrap[^"]*"[^>]*>)(.*?)(</div>\s*</section>)',
                    re.DOTALL | re.IGNORECASE
                )
                m = faq_pat.search(html)
                if m:
                    html = html[:m.start()] + m.group(1) + wrapped_faq + m.group(3) + html[m.end():]
                    changes.append("updated FAQ section")

    # Sanity: no duplicate AI blocks (catches double-inject bugs)
    assert html.count(_AI_BLOCK_START) <= 1, "Duplicate AI block detected!"
    assert html.count(_AI_FAQ_START) <= 1, "Duplicate FAQ block detected!"

    return html, changes

# ── Load data ─────────────────────────────────────────────────────────────────
print("=" * 60)
print("🔧 TSJ AI HTML Patcher")
print("=" * 60)

if not DATA_FILE.exists():
    print(f"❌ {DATA_FILE} not found")
    sys.exit(1)

print(f"📂 Loading {DATA_FILE}...")
with open(DATA_FILE, encoding="utf-8") as f:
    master = json.load(f)

# Collect all AI-enriched sarkari jobs
sark_jobs = master.get("sarkari_data", {}).get("jobs", [])
ai_jobs   = [j for j in sark_jobs if j.get("ai_overview") and get_slug(j)]
print(f"✅ {len(ai_jobs)} sarkari jobs have AI data")

if SINGLE:
    ai_jobs = [j for j in ai_jobs if get_slug(j) == SINGLE]
    print(f"🔍 Single mode: {SINGLE} → {len(ai_jobs)} match(es)")

print(f"{'🔵 DRY RUN — no files written' if DRY_RUN else '✏️  Writing files...'}")
print()

# ── Process ───────────────────────────────────────────────────────────────────
patched   = 0
skipped   = 0
not_found = 0
errors    = 0

for job in ai_jobs:
    slug    = get_slug(job)
    html_path = JOBS_DIR / slug / "index.html"

    if not html_path.exists():
        not_found += 1
        if SINGLE:
            print(f"  ❌ Not found: {html_path}")
        continue

    try:
        original = html_path.read_text(encoding="utf-8")
        new_html, changes = patch_html(original, job)

        if not changes:
            skipped += 1
            continue

        if DRY_RUN:
            print(f"  🔵 Would patch [{slug[:55]}]: {', '.join(changes)}")
            patched += 1
        else:
            # Atomic write
            tmp = html_path.with_suffix(".tmp")
            tmp.write_text(new_html, encoding="utf-8")
            tmp.replace(html_path)
            print(f"  ✅ Patched [{slug[:55]}]: {', '.join(changes)}")
            patched += 1

    except Exception as ex:
        print(f"  ❌ Error [{slug[:50]}]: {ex}")
        errors += 1

print()
print("=" * 60)
print(f"  ✅ Patched   : {patched}")
print(f"  ⏭️  Skipped   : {skipped} (already had AI data)")
print(f"  ❓ Not found : {not_found} (HTML not built yet)")
print(f"  ❌ Errors    : {errors}")
print("=" * 60)
if patched > 0 and not DRY_RUN:
    print("\n✨ Done! Commit these changes:")
    print("  git add jobs/")
    print('  git commit -m "🤖 AI content patched into existing HTML pages"')
    print("  git push")
