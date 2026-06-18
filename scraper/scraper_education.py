# -*- coding: utf-8 -*-
# ================================================================
# SCRAPER: Education Jobs — scraper_education.py
# ================================================================
# Source  : freejobalert.com/education/
# Writes  : Education_Jobs.json  (intermediate)
# Output  : Updates "education_jobs" in Complete_Jobs_Full_Data.json
#           Baaki teen sources (fja, sarkari, state) UNCHANGED rehte hain.
#
# Run:  python scraper_education.py
# ================================================================

import sys
sys.stdout.reconfigure(encoding="utf-8")

# SOURCE 3: EDUCATION JOBS (EDUCATION.py)
# ================================================================

import requests
from bs4 import BeautifulSoup
import os
import json, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed


# =====================================
# CONFIG
# =====================================

EDUCATION_URL = "https://www.freejobalert.com/education/"
EDU_OUTPUT_FILE = "Education_Jobs.json"
TOP_N_ROWS    = 50
EDU_MAX_WORKERS = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

BLOCKED_DOMAINS = [
    "freejobalert.com", "slate.freejobalert.com", "play.google.com",
    "apps.apple.com", "whatsapp.com", "news.google.com", "rebrand.ly",
    "arattai.in", "t.me", "facebook.com", "twitter.com", "instagram.com",
    "youtube.com", "linkedin.com", "telegram.me",
    "tbresults.tripura.gov.in",
]

# Categories to completely skip — no rows will be collected from these
SKIP_CATEGORIES = {
    "all india engineering",
    "all india medical",
    "all india management",
    "all india entrance",
    "all india exams",
    "cbse/icse 10th",
    "cbse/icse 12th",
}

SKIP_DIV_CLASSES = {
    "ad_div", "linestyle", "fja-follow-bar", "fja-alert-widget",
    "advertisement", "sidebar", "related-posts", "sharedaddy",
}

# Strings that signal a junk row — skip entire row if cell contains these
SKIP_ROW_KEYWORDS = [
    "www.freejobalert.com", "freejobalert",
    "download mobile app", "download app",
    "join telegram", "join whatsapp", "join instagram", "join youtube",
    "follow us", "subscribe", "click here for more",
    "interested candidates can read",
    "@ tbresults.tripura.gov.in", "tbresults.tripura.gov.in",
]

# Strings that signal the "Important Links" divider row inside a table
LINK_SECTION_LABELS = {
    "important links", "important link", "useful links",
    "important links:", "useful links:",
}

# Known merged-cell section prefixes (old freejobalert format)
MERGED_SECTION_PREFIXES = [
    "application fee", "important dates", "age limit", "qualification",
    "physical standards", "eligibility", "vacancy details", "exam details",
    "exam name", "post name", "selection process", "salary", "pay scale",
    "how to apply", "documents required",
]

# =====================================
# HELPERS
# =====================================

def edu_clean_text(text):
    return " ".join((text or "").replace("\xa0", " ").split()).strip()

def edu_create_id(name):
    return (
        name.lower().replace("&","and").replace(",","")
        .replace("/","-").replace(" ","-")
    )

def edu_is_valid_link(href):
    if not href or not href.startswith("http"):
        return False
    hl = href.lower()
    return not any(d in hl for d in BLOCKED_DOMAINS)

def is_skip_div(tag):
    return bool(set(tag.get("class", [])) & SKIP_DIV_CLASSES)

def should_skip_row_text(text):
    tl = text.lower()
    return any(kw in tl for kw in SKIP_ROW_KEYWORDS)

def is_link_section_label(cells):
    return len(cells) == 1 and cells[0].lower().strip() in LINK_SECTION_LABELS

def is_click_here_row(cells):
    """2-col row where col[1] is 'Click Here' or similar."""
    if len(cells) == 2:
        return cells[1].lower().strip() in {"click here", "click here.", "get details", "view result", "apply now"}
    return False

def is_merged_section_row(text):
    """Single long cell that starts with a known section prefix."""
    tl = text.lower().strip()
    return any(tl.startswith(p) for p in MERGED_SECTION_PREFIXES)

def split_merged_cell(text):
    """
    'Application Fee For All: Rs.200 For SC: Nil Mode: Online'
    → { "label": "Application Fee", "text": "For All: Rs.200 For SC: Nil Mode: Online" }
    """
    for prefix in MERGED_SECTION_PREFIXES:
        if text.lower().startswith(prefix):
            rest = text[len(prefix):].strip()
            return {"label": prefix.title(), "text": rest}
    return {"label": "", "text": text}

# =====================================
# PARSE TABLE — fully smart
# =====================================

def parse_table(table):
    """
    Returns one of:
      {"type":"table",           "headers":[...], "rows":[[...]]}
      {"type":"important_links", "links":[{"label","url"}]}
      {"type":"merged_info",     "items":[{"label","text"}]}
      None  — if nothing useful
    """
    all_tr = table.find_all("tr")

    # Collect raw row data: cells text + anchor tags
    raw = []
    for tr in all_tr:
        ths = tr.find_all("th")
        tds = tr.find_all("td")
        cells = [edu_clean_text(c.get_text()) for c in (ths or tds)]
        anchors = []
        for td in (tds or ths):
            for a in td.find_all("a", href=True):
                href = a["href"].strip()
                if edu_is_valid_link(href):
                    anchors.append({
                        "label": edu_clean_text(a.get_text()),
                        "url": href,
                    })
        is_header = bool(ths and not tds)
        raw.append({"cells": cells, "anchors": anchors, "is_header": is_header})

    # Separate header row
    headers = []
    data_raw = []
    for r in raw:
        if r["is_header"] and not headers:
            headers = r["cells"]
        else:
            data_raw.append(r)

    # Filter junk rows
    filtered = []
    for r in data_raw:
        combined = " ".join(r["cells"])
        if should_skip_row_text(combined):
            continue
        if is_link_section_label(r["cells"]):
            continue
        filtered.append(r)

    if not filtered:
        return None

    # ── Detect table type ────────────────────────────

    # Count different row types
    click_rows   = [r for r in filtered if is_click_here_row(r["cells"]) and r["anchors"]]
    merged_rows  = [r for r in filtered if len(r["cells"]) == 1 and is_merged_section_row(r["cells"][0])]
    normal_rows  = [r for r in filtered
                    if not is_click_here_row(r["cells"])
                    and not (len(r["cells"]) == 1 and is_merged_section_row(r["cells"][0]))]

    # ── Case A: Mostly merged-cell rows (old freejobalert format) ──
    if len(merged_rows) >= 2 and len(merged_rows) >= len(normal_rows):
        items = []
        for r in filtered:
            if len(r["cells"]) == 1:
                txt = r["cells"][0]
                if is_merged_section_row(txt):
                    items.append(split_merged_cell(txt))
                elif len(txt) < 60:
                    # short single-col like "Vacancy Details" header — skip
                    pass
                # Long non-prefix single cell — skip (garbage)
            elif len(r["cells"]) == 2:
                # Could be a sub-table like "Exam Name | Total Seats"
                items.append({"label": r["cells"][0], "text": r["cells"][1]})
        if items:
            return {"type": "merged_info", "items": items}
        return None

    # ── Case B: Has mix of link rows + data rows — split them ──
    if click_rows and normal_rows:
        # Return two entries: data table + important_links
        # We'll handle this in the caller by returning a list
        data_table_rows = []
        for r in filtered:
            if is_click_here_row(r["cells"]) and r["anchors"]:
                continue   # will go to links
            if len(r["cells"]) >= 1:
                data_table_rows.append(r["cells"])

        links = []
        for r in filtered:
            if is_click_here_row(r["cells"]) and r["anchors"]:
                for a in r["anchors"]:
                    links.append({"label": r["cells"][0], "url": a["url"]})

        result = []
        if data_table_rows:
            result.append({"type": "table", "headers": headers, "rows": data_table_rows})
        if links:
            result.append({"type": "important_links", "links": links})
        return result if result else None

    # ── Case C: Pure important_links table ──
    if click_rows and not normal_rows:
        links = []
        for r in filtered:
            if r["anchors"]:
                for a in r["anchors"]:
                    links.append({"label": r["cells"][0], "url": a["url"]})
        return {"type": "important_links", "links": links} if links else None

    # ── Case D: Normal data table ──
    rows_out = [r["cells"] for r in filtered]
    return {"type": "table", "headers": headers, "rows": rows_out} if rows_out else None

# =====================================
# ADD TO SECTION — handles list return
# =====================================

def add_parsed(parsed, section, detail):
    """Add parse_table() result (single dict or list) to current section."""
    if parsed is None:
        return
    entries = parsed if isinstance(parsed, list) else [parsed]
    for entry in entries:
        if entry["type"] == "important_links":
            # Merge into detail-level important_links.structured_links
            detail["important_links"].setdefault("structured_links", [])
            for lnk in entry["links"]:
                # avoid duplicates
                if lnk not in detail["important_links"]["structured_links"]:
                    detail["important_links"]["structured_links"].append(lnk)
        section["content"].append(entry)

# =====================================
# SCRAPE DETAIL PAGE
# =====================================

def scrape_detail(page_url):
    try:
        resp    = requests.get(page_url, headers=HEADERS, timeout=20)
        soup    = BeautifulSoup(resp.text, "html.parser")
        content = (
            soup.find("div", class_="entry-content") or
            soup.find("div", class_="post-content")  or
            soup.find("article") or soup.find("main")
        )
        if not content:
            return {}

        detail = {
            "title":           "",
            "short_info":      "",
            "sections":        [],
            "important_links": {},
            "seo_tags":        [],
        }

        # Meta
        meta = soup.find("meta", {"name": "description"})
        if meta and meta.get("content"):
            detail["short_info"] = edu_clean_text(meta["content"])

        kw = soup.find("meta", {"name": "keywords"})
        if kw and kw.get("content"):
            detail["seo_tags"] = [k.strip() for k in kw["content"].split(",") if k.strip()]
        if not detail["seo_tags"]:
            pt = soup.find("title")
            if pt:
                detail["seo_tags"].append(edu_clean_text(pt.get_text()))

        # All valid links
        valid_links  = []
        official_url = None
        notif_pdf    = None
        for a in soup.find_all("a", href=True):
            href      = a["href"].strip()
            link_text = edu_clean_text(a.get_text()).lower()
            if not edu_is_valid_link(href):
                continue
            valid_links.append(href)
            if ".pdf" in href.lower() and not notif_pdf:
                notif_pdf = href
            if not official_url and any(kw in link_text for kw in [
                "apply online","official website","apply here","apply now",
                "check result","download","click here","official link",
                "official notification","direct link",
            ]):
                official_url = href

        if not official_url:
            non_pdf = [l for l in valid_links if ".pdf" not in l.lower()]
            if non_pdf:
                official_url = non_pdf[0]

        valid_links = list(dict.fromkeys(valid_links))[:5]
        if valid_links:
            detail["important_links"]["click_here"] = valid_links
        if notif_pdf:
            detail["important_links"]["notification_pdf"] = notif_pdf
        detail["_official_url"] = official_url or ""

        # Walk children in document order
        current_section = None

        def flush():
            if current_section and (current_section["heading"] or current_section["content"]):
                detail["sections"].append(current_section)

        children = [c for c in content.children if hasattr(c,"name") and c.name]

        for child in children:
            tag = child.name
            cls = set(child.get("class") or [])
            txt = edu_clean_text(child.get_text())

            if tag == "div" and is_skip_div(child):
                continue

            # ── Heading → new section ─────────────
            if tag in ["h1","h2","h3","h4","h5","h6"]:
                flush()
                current_section = {"heading": txt, "content": []}
                # Fill title: prefer h1, fallback to first h2
                if not detail["title"] and tag in ["h1","h2"]:
                    detail["title"] = txt

            # ── Paragraph ─────────────────────────
            elif tag == "p":
                if not txt:
                    continue
                if any(s in txt for s in ["Join WhatsApp","Join Telegram","Advertisement","FOLLOW US","tbresults.tripura.gov.in"]):
                    continue
                entry = {"type": "paragraph", "text": txt}
                p_links = []
                for a in child.find_all("a", href=True):
                    href = a["href"].strip()
                    if edu_is_valid_link(href):
                        p_links.append({"text": edu_clean_text(a.get_text()), "url": href})
                if p_links:
                    entry["links"] = p_links
                if current_section is None:
                    current_section = {"heading": "", "content": []}
                current_section["content"].append(entry)

            # ── List ──────────────────────────────
            elif tag in ["ul","ol"]:
                items = [edu_clean_text(li.get_text()) for li in child.find_all("li") if edu_clean_text(li.get_text())]
                if not items:
                    continue
                if current_section is None:
                    current_section = {"heading": "", "content": []}
                current_section["content"].append({
                    "type":  "list",
                    "style": "ordered" if tag == "ol" else "unordered",
                    "items": items,
                })

            # ── DIV ───────────────────────────────
            elif tag == "div":
                if "table-container" in cls:
                    inner = child.find("table")
                    if inner:
                        if current_section is None:
                            current_section = {"heading": "", "content": []}
                        add_parsed(parse_table(inner), current_section, detail)
                elif txt and not child.find(["table","ul","ol","div"]):
                    if "Join WhatsApp" in txt or "FOLLOW US" in txt or "tbresults.tripura.gov.in" in txt:
                        continue
                    if current_section is None:
                        current_section = {"heading": "", "content": []}
                    current_section["content"].append({"type":"paragraph","text":txt})

            # ── Standalone table ──────────────────
            elif tag == "table":
                if current_section is None:
                    current_section = {"heading": "", "content": []}
                add_parsed(parse_table(child), current_section, detail)

        flush()
        return detail

    except Exception as e:
        print(f"    DETAIL ERROR [{page_url}]: {e}")
        return {}

# =====================================
# PROCESS ONE LIST ROW
# =====================================

def process_row(args):
    category, cols = args
    try:
        post_date = edu_clean_text(cols[0].get_text())
        exam_name = edu_clean_text(cols[1].get_text())
        link_tag  = cols[2].find("a", href=True)
        if not link_tag:
            return None

        page_url = link_tag["href"].strip()
        if page_url.startswith("/"):
            page_url = "https://www.freejobalert.com" + page_url

        print(f"    → [{category[:28]}] {exam_name[:55]}")

        detail = scrape_detail(page_url)
        if not detail:
            return None

        title        = detail.get("title") or exam_name
        official_url = detail.pop("_official_url", "") or ""

        return {
            "name":     title,
            "url":      official_url,
            "_scraped_from": page_url,   # INTERNAL ONLY — incremental-scrape
                                          # bookkeeping, never rendered.
            "date":     f"Post Date: {post_date}",
            "postDate": post_date,
            "examName": exam_name,
            "category": f"EDUCATION - {category}",
            "detail":   detail,
        }
    except Exception as e:
        print(f"    ROW ERROR [{category}]: {e}")
        return None

# =====================================
# GET CATEGORY HEADING
# =====================================

def get_category(table, container):
    prev = table.find_previous()
    while prev and prev != container:
        if prev.name in ["h1","h2","h3","h4","h5","h6","strong","b"]:
            txt = edu_clean_text(prev.get_text())
            if txt and len(txt) < 120 and "Post Date" not in txt:
                return txt
        elif prev.name in ["p","div","span","td","li"]:
            txt = edu_clean_text(prev.get_text())
            if 3 < len(txt) < 80 and "Post Date" not in txt and "More Information" not in txt:
                return txt
        prev = prev.find_previous()
    return "Education & Entrance Exam Notifications"

# =====================================
# MAIN
# =====================================

def scrape_education():
    print("=" * 58)
    print("  EDUCATION SCRAPER — freejobalert.com/education/")
    print("=" * 58)

    resp = requests.get(EDUCATION_URL, headers=HEADERS, timeout=30)
    print(f"  Status: {resp.status_code}  |  Page: {len(resp.text):,} bytes")

    # SAFETY: if the education page is down / moved (404/5xx), DON'T proceed to
    # write an empty file over good data — abort and keep existing JSON.
    if resp.status_code != 200:
        print(f"\n[ABORT] Education page returned HTTP {resp.status_code} "
              f"({EDUCATION_URL}) — keeping EXISTING data, no stale-overwrite.")
        return None

    soup      = BeautifulSoup(resp.text, "html.parser")
    container = soup.find("div", class_="lsntsdiv")
    if not container:
        container = (
            soup.find("div", id="content") or
            soup.find("div", class_="entry-content") or
            soup.find("main") or soup.find("article") or soup.body
        )
        print("  NOTE: lsntsdiv not found — fallback used")
    else:
        print("  Container: lsntsdiv ✓")

    tables   = container.find_all("table") if container else []
    print(f"  Tables found: {len(tables)}")

    all_rows = []
    for table in tables:
        category = get_category(table, container)
        # Skip the 7 blocked categories entirely
        if category.lower().strip() in SKIP_CATEGORIES:
            print(f"  SKIPPED category: {category}")
            continue
        count    = 0
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) == 3 and cols[2].find("a", href=True):
                all_rows.append((category, cols))
                count += 1
                if count >= TOP_N_ROWS:
                    break

    print(f"  Total rows collected: {len(all_rows)}")

    # ── INCREMENTAL SCRAPE: load whatever we already have so we only hit the
    # detail page for rows that are genuinely new (same pattern used across
    # the other scrapers). Cuts education-section requests from "every row,
    # every run" down to just new postings. ──
    _existing_items_by_cat = {}
    if os.path.exists(EDU_OUTPUT_FILE):
        try:
            with open(EDU_OUTPUT_FILE, encoding="utf-8") as _f:
                _prev = json.load(_f)
            for _sec in _prev.get("sections", []):
                _existing_items_by_cat[_sec.get("title", "")] = _sec.get("items", [])
        except Exception as _e:
            print(f"  [INCREMENTAL] could not load previous {EDU_OUTPUT_FILE}: {_e}")

    def _row_page_url(cols):
        """Cheaply pull the detail-page URL from a row without scraping it."""
        try:
            link_tag = cols[2].find("a", href=True)
            if not link_tag:
                return ""
            u = link_tag["href"].strip()
            if u.startswith("/"):
                u = "https://www.freejobalert.com" + u
            return u
        except Exception:
            return ""

    _carry_forward_items = {}   # category -> [item, ...]
    _new_all_rows = []
    _skipped_count = 0
    for category, cols in all_rows:
        _existing_urls = {it.get("_scraped_from", "") for it in
                          _existing_items_by_cat.get(category, []) if it.get("_scraped_from")}
        _existing_by_url = {it["_scraped_from"]: it for it in
                            _existing_items_by_cat.get(category, []) if it.get("_scraped_from")}
        _link = _row_page_url(cols)
        if _link and _link in _existing_urls:
            _carry_forward_items.setdefault(category, []).append(_existing_by_url[_link])
            _skipped_count += 1
        else:
            _new_all_rows.append((category, cols))
    print(f"  [INCREMENTAL] {_skipped_count} rows already scraped (skipped), "
          f"{len(_new_all_rows)} new rows to fetch")
    all_rows = _new_all_rows

    # Scrape in parallel but PRESERVE original row order (as_completed returns
    # in random completion order). Store each result at its source index.
    category_items = {}
    # seed with carried-forward (already-scraped) items first
    for _cat, _items in _carry_forward_items.items():
        category_items.setdefault(_cat, []).extend(_items)
    results_by_idx = [None] * len(all_rows)
    with ThreadPoolExecutor(max_workers=EDU_MAX_WORKERS) as executor:
        futures = {executor.submit(process_row, args): idx
                   for idx, args in enumerate(all_rows)}
        for future in as_completed(futures):
            idx = futures[future]
            cat = all_rows[idx][0]
            try:
                item = future.result()
                if item:
                    results_by_idx[idx] = item
            except Exception as e:
                print(f"  FUTURE ERROR [{cat}]: {e}")

    # Re-assemble in original order
    for idx, (cat, _cols) in enumerate(all_rows):
        item = results_by_idx[idx]
        if item:
            category_items.setdefault(cat, []).append(item)

    seen = []
    # IMPORTANT: include categories that had ZERO new rows (fully carried
    # forward) — otherwise their section would silently disappear.
    for cat in list(category_items.keys()):
        if cat not in seen:
            seen.append(cat)

    final_json = {"sections": []}
    for cat in seen:
        items = category_items.get(cat, [])
        if not items:
            continue
        items.sort(key=lambda x: x.get("postDate",""), reverse=True)
        final_json["sections"].append({
            "id":       edu_create_id(cat),
            "title":    cat,
            "category": f"EDUCATION - {cat}",
            "type":     "education",
            "items":    items,
        })

    # SAFETY: never write an empty sections file over good existing data.
    if not final_json["sections"]:
        print("\n[ABORT] Parsed 0 education sections — keeping EXISTING JSON "
              "(no stale-overwrite).")
        return None

    with open(EDU_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=4, ensure_ascii=False)

    total_cats  = len(final_json["sections"])
    total_items = sum(len(s["items"]) for s in final_json["sections"])

    print("\n" + "=" * 58)
    print("  EDUCATION SCRAPING COMPLETE")
    print(f"  Categories  : {total_cats}")
    print(f"  Total Items : {total_items}")
    print(f"  Output      : {EDU_OUTPUT_FILE}")
    print("=" * 58)


# ================================================================


# ================================================================
# MERGE INTO UNIFIED JSON
# ================================================================
if __name__ == "__main__":
    from scraper_merge import merge_into_json, wait_for_internet
    import json as _json_mod, os

    wait_for_internet("Education")

    print("\n" + "="*60)
    print("  SCRAPER: Education Jobs")
    print("="*60)

    error_str = ""
    try:
        scrape_education()   # saves to Education_Jobs.json
    except Exception as e:
        import traceback; traceback.print_exc()
        error_str = str(e)

    scraped = {}
    if os.path.exists("Education_Jobs.json"):
        with open("Education_Jobs.json", encoding="utf-8") as f:
            scraped = _json_mod.load(f)

    merge_into_json(
        source        = "education_jobs",
        fresh_data    = scraped,
        scraper_error = error_str,
    )
