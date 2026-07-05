#!/usr/bin/env python3
"""
fix_duplicate_overview_faq.py — One-time cleanup
=================================================
Jo pages pehle se enrich ho chuke hain (AI_MARKER wale) aur unme 2 Overview
ya 2 FAQ ban chuke hain — is script se un duplicates ko saaf karo.

Koi Groq API call NAHI lagti. Sirf local file I/O + regex hai, isliye
sabhi ~3600+ pages ek hi run mein process ho jaate hain, free & fast.

Logic:
  1. Har jobs/*/index.html file kholo.
  2. Agar AI_MARKER (<!-- tsj-ai-enriched -->) present hai, uska block
     nikaalo — ye ai_html_enricher.py ne inject kiya hua content hai.
  3. Base HTML (AI block ke bahar) mein dekho ki wahan already ek "...
     Overview" ya "... FAQ" heading maujood hai ya nahi.
  4. Agar haan — to AI block ke andar se sirf uska Overview/FAQ card hata do
     (baaki 6 unique AI cards — Expert Analysis, Who Should Apply, etc. —
     waise hi rehne do, wo genuinely naye hain, duplicate nahi).
  5. Final safety net: poore page pe generate_all.py wala hi
     _dedup_section_cards() bhi chala do (kisi aur accidental duplicate ke
     liye).
  6. Sirf tabhi file likho jab kuch change hua ho.

Usage:
  python3 fix_duplicate_overview_faq.py                # sab pages
  python3 fix_duplicate_overview_faq.py --dry-run       # sirf report, likhna nahi
  python3 fix_duplicate_overview_faq.py --slug <slug>   # ek page test
"""

import sys, re
from pathlib import Path

# ai_html_enricher.py se hi zaroori functions reuse karo — copy-paste se
# dono files kabhi out-of-sync na ho.
sys.path.insert(0, str(Path(__file__).parent))
from ai_html_enricher import AI_MARKER, _dedup_section_cards

JOBS_DIR = Path("jobs")
DRY_RUN = "--dry-run" in sys.argv
SINGLE_SLUG = None
for i, a in enumerate(sys.argv):
    if a == "--slug" and i + 1 < len(sys.argv):
        SINGLE_SLUG = sys.argv[i + 1]

_OVERVIEW_RE = re.compile(r"\boverview\b", re.I)
_FAQ_RE = re.compile(r"\bfaqs?\b|\bfrequently\s+asked\s+questions\b", re.I)

# Purane runs mein (title-prefix feature add hone se pehle) AI cards ye
# "bare" (bina title ke) headings ke saath patch hue the. Ab in exact
# headings ko dhoond ke title-prefixed version se replace karna hai.
_BARE_HEADING_TEMPLATES = {
    "overview":             "{t} Overview",
    "expert analysis":      "{t} Expert Analysis",
    "who should apply":     "Who Should Apply {t}",
    "preparation tips":     "{t} Preparation Tips",
    "salary insights":      "{t} Salary Insights",
    "job profile":          "{t} Job Profile",
    "selection strategy":   "{t} Selection Strategy",
    "faqs":                 "{t} FAQs",
    "faq":                  "{t} FAQs",
}


def _extract_title(html: str) -> str:
    """<title> tag se clean job-title nikaalo (brand-name hata ke) — same
    logic jo ai_html_enricher.py ke extract_facts() mein use hota hai."""
    m = re.search(r"<title>([^<]+)</title>", html)
    if not m:
        return ""
    import html as _html
    return _html.unescape(m.group(1)).replace(" | Top Sarkari Jobs", "").strip()


def _headings(html: str) -> list[str]:
    return re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.I | re.S)


def _split_into_cards(ai_block: str) -> list[str]:
    """AI block ko individual sec-card pieces mein todo (heading ke saath),
    non-card leading whitespace/text alag rakho."""
    return re.split(r"(?=<section class=\"sec-card\">)", ai_block)


def clean_file(html: str) -> tuple[str, dict]:
    """Returns (new_html, stats) — stats batata hai kya-kya hataya/badla gaya."""
    stats = {"overview_removed": False, "faq_removed": False,
             "dedup_extra": False, "titles_added": 0}

    if AI_MARKER not in html:
        return html, stats

    job_title = _extract_title(html)

    # AI_MARKER hamesha pairs mein hota hai (open ... close). Har pair ko
    # dhoondo aur uske andar se duplicate card hatao + bare heading mein
    # title inject karo.
    pattern = re.compile(re.escape(AI_MARKER) + r"(.*?)" + re.escape(AI_MARKER), re.S)

    def _process_block(m):
        block = m.group(1)
        outside_html = html[:m.start()] + html[m.end():]
        base_has_overview = bool(_OVERVIEW_RE.search(" ".join(_headings(outside_html))))
        base_has_faq = bool(_FAQ_RE.search(" ".join(_headings(outside_html))))

        pieces = _split_into_cards(block)
        kept = []
        for p in pieces:
            hm = re.search(r"<h2[^>]*>(.*?)</h2>", p, re.I | re.S)
            heading = hm.group(1) if hm else ""

            # 1. Duplicate removal (Overview/FAQ jinke base mein already hain)
            if base_has_overview and _OVERVIEW_RE.search(heading) and "faq" not in heading.lower():
                stats["overview_removed"] = True
                continue
            if base_has_faq and _FAQ_RE.search(heading):
                stats["faq_removed"] = True
                continue

            # 2. Bare heading mein title inject karo (agar title available hai
            #    aur heading abhi exact "bare" form mein hai — purane
            #    patch se, title-prefix feature se pehle wali)
            if heading and job_title:
                bare_key = re.sub(r"\s+", " ", heading).strip().lower()
                tmpl = _BARE_HEADING_TEMPLATES.get(bare_key)
                if tmpl:
                    new_heading = tmpl.format(t=job_title)
                    p = p.replace(f"<h2>{hm.group(1)}</h2>", f"<h2>{new_heading}</h2>", 1)
                    stats["titles_added"] += 1

            kept.append(p)
        return AI_MARKER + "".join(kept) + AI_MARKER

    new_html = pattern.sub(_process_block, html)

    # Khaali marker-pairs saaf karo (tab bante hain jab ek AI block ka poora
    # card hi duplicate nikla ho aur andar kuch bacha na ho)
    new_html = re.sub(re.escape(AI_MARKER) + r"\s*" + re.escape(AI_MARKER), "", new_html)

    # Final catch-all safety net (same as generate_all.py's own de-dup).
    deduped = _dedup_section_cards(new_html)
    if deduped != new_html:
        stats["dedup_extra"] = True
    new_html = deduped

    return new_html, stats


def main():
    if not JOBS_DIR.exists():
        print(f"❌ {JOBS_DIR} not found — run from repo root")
        sys.exit(1)

    files = [JOBS_DIR / SINGLE_SLUG / "index.html"] if SINGLE_SLUG else sorted(JOBS_DIR.rglob("index.html"))

    scanned = fixed = overview_fixed = faq_fixed = extra_dedup = titles_added = 0
    fixed_slugs = []

    for f in files:
        if not f.exists():
            print(f"  ❌ Not found: {f}")
            continue
        scanned += 1
        try:
            original = f.read_text(encoding="utf-8")
        except Exception as ex:
            print(f"  ❌ Read error [{f}]: {ex}")
            continue

        new_html, stats = clean_file(original)

        if new_html != original:
            fixed += 1
            if stats["overview_removed"]:
                overview_fixed += 1
            if stats["faq_removed"]:
                faq_fixed += 1
            if stats["dedup_extra"]:
                extra_dedup += 1
            titles_added += stats["titles_added"]
            fixed_slugs.append(f.parent.name)
            tag = []
            if stats["overview_removed"]: tag.append("Overview")
            if stats["faq_removed"]: tag.append("FAQ")
            if stats["dedup_extra"]: tag.append("extra-dedup")
            if stats["titles_added"]: tag.append(f"+title x{stats['titles_added']}")
            print(f"  🧹 {f.parent.name}  [{', '.join(tag)}]")
            if not DRY_RUN:
                tmp = f.with_suffix(".tmp")
                tmp.write_text(new_html, encoding="utf-8")
                tmp.replace(f)

    print()
    print("=" * 60)
    print("  📋 DUPLICATE CLEANUP — REPORT")
    print("=" * 60)
    print(f"  📄 Scanned          : {scanned}")
    print(f"  🧹 Fixed            : {fixed}")
    print(f"     ├─ Overview de-dup : {overview_fixed}")
    print(f"     ├─ FAQ de-dup      : {faq_fixed}")
    print(f"     ├─ Titles added    : {titles_added}")
    print(f"     └─ Extra safety-net: {extra_dedup}")
    print(f"  ✅ Untouched        : {scanned - fixed}")
    print(f"  Mode                : {'DRY RUN (nothing written)' if DRY_RUN else 'LIVE (files written)'}")
    print("=" * 60)
    if fixed_slugs[:10]:
        print("  Sample fixed slugs:", ", ".join(fixed_slugs[:10]))


if __name__ == "__main__":
    main()
