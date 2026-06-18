#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================================
# SCRAPER: State Govt Jobs — scraper_state.py
# ================================================================
# Source  : freejobalert.com/state-government-jobs/
# Writes  : State_Wise_Jobs.json  (intermediate)
# Output  : Updates "state_jobs" in Complete_Jobs_Full_Data.json
#           Baaki teen sources (fja, sarkari, education) UNCHANGED rehte hain.
#
# Run:  python scraper_state.py
# ================================================================

import sys
sys.stdout.reconfigure(encoding="utf-8")

# SOURCE 4: STATE GOVT JOBS (STATE.py)
# ================================================================

import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


# =====================================
# BLOCKED DOMAINS — all irrelevant links
# =====================================

BLOCKED_DOMAINS = [
    "freejobalert.com",
    "slate.freejobalert.com",
    "play.google.com",
    "apps.apple.com",
    "whatsapp.com",
    "news.google.com",
    "rebrand.ly",
    "arattai.in",
    "t.me",
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "youtube.com",
    "linkedin.com",
    "telegram.me",
]

# Keywords that signal a useful official/job link
USEFUL_LINK_KEYWORDS = [
    ".pdf", "apply", "notification", "recruitment", "vacancy",
    "advt", "advertisement", "career", "job", "admit", "result",
    "syllabus", "official", "gov", "nic.in", "ac.in", "org.in"
]

def state_is_valid_link(href):
    """
    Return True only if:
    - NOT from any blocked domain
    - Looks like an actual official / job-related link
    """
    if not href or not href.startswith("http"):
        return False
    href_lower = href.lower()
    for domain in BLOCKED_DOMAINS:
        if domain in href_lower:
            return False
    # Must contain at least one useful keyword
    for kw in USEFUL_LINK_KEYWORDS:
        if kw in href_lower:
            return True
    return False


# =====================================
# CLEAN TEXT
# =====================================

def state_clean_text(text):
    return " ".join((text or "").split()).strip()


# ── Noise filter for selection_process ──────────────────────────────────────
# State job pages mein website sidebar/footer content selection_process mein
# ghus jaata hai — nav links, job listings, city counts, tool names etc.
# Ye filter unhe reject karta hai, actual steps accept karta hai.
import re as _re_state

_SELECTION_NOISE_RE = _re_state.compile(
    r'^(?:'
    r'Latest Notifications|Employment News|Search Jobs|Sarkari\s+\w+|'
    r'Anganwadi.*|Forest Jobs|EDUCATION|Free Mock Test|Admit Card|'
    r'Exam Results|Answer Key|Cutoff Marks|Written Marks|Interview Results|'
    r'Last Date Reminder|Eligibility|Syllabus|Exam Pattern|Previous Papers|'
    r'Selection Process|'
    r'Games|Image Resizer|.*Converter|Free AI.*|'
    # Sidebar job listings: "CISF ASI Online Form 2026", "SBI Apprentice Online Form 2026"
    r'.*\b(?:Online Form|Offline Form)\s+20\d\d.*|'
    # City-count: "Hyderabad Jobs (459)", "New Delhi (26758)"
    r'.+\(\d{2,6}\)$|'
    # Qualification nav labels: "10TH Jobs", "B.Tech/B.E Jobs"
    r'(?:10TH|8TH|12TH|Diploma|ITI|B\.?Tech(?:/B\.?E)?|B\.?com|MBA|MSW|B\.?sc|M\.?sc|BA|MA|'
    r'Any Graduate|Any Post Graduate)\s+Jobs|'
    # Sidebar result/admit/answer key listings
    r'.+(?:Admit Card|Result|Answer Key|Syllabus|Exam Pattern)\s+20\d\d.*'
    r')$',
    _re_state.I
)

def _is_selection_noise(text):
    """True agar text website nav/sidebar se hai, actual selection step nahi."""
    t = text.strip()
    if len(t) < 8:
        return True
    if _SELECTION_NOISE_RE.match(t):
        return True
    # Sidebar job listings:
    # "XYZ Recruitment 2026 - Apply Online"
    # "XYZ Recruitment 2026 Notification Out For 24 Posts, Apply Online..."
    # "XYZ Recruitment 2026 - Apply Offline"
    # "XYZ Recruitment 2026 - Walkin for 12 Posts"
    if _re_state.search(
        r'\b(?:Recruitment|Vacancy|Walkin|Walk-?in)\s+20\d\d\b',
        t, _re_state.I
    ):
        return True
    # FJA sidebar "Related Jobs" listings that slip through:
    # Pattern: ends with " - Apply Online/Offline" or " - Walkin"
    if _re_state.search(r'\s[-–]\s+Apply\s+(?:Online|Offline|Now)\s*$', t, _re_state.I):
        return True
    if _re_state.search(r'\s[-–]\s+Walk\s*[- ]?in\b', t, _re_state.I):
        return True
    return False


# =====================================
# CREATE ID
# =====================================

def state_create_id(state):
    return (
        state.lower()
        .replace("&", "and")
        .replace(",", "")
        .replace(" ", "-")
    )


# =====================================
# SCRAPE DETAILED JOB PAGE
# FJA Article-aware parser — Overview table, Important Dates,
# Vacancy Details, Important Links, FAQ — sab properly extract
# =====================================

# ── FJA Overview table ke known key mappings ─────────────────
_FJA_OVERVIEW_KEY_MAP = {
    # Organization / Board
    "organization name":      ("basic_details", "organization_name"),
    "company name":           ("basic_details", "organization_name"),
    "board name":             ("basic_details", "organization_name"),
    "department name":        ("basic_details", "organization_name"),
    "advt no":                ("basic_details", "advt_no"),
    "advertisement no":       ("basic_details", "advt_no"),
    "advertisement no.":      ("basic_details", "advt_no"),
    "exam name":              ("basic_details", "exam_name"),
    "post name":              ("basic_details", "post_name"),
    "post names":             ("basic_details", "post_name"),
    "no of posts":            ("basic_details", "total_vacancies"),
    "total posts":            ("basic_details", "total_vacancies"),
    "total vacancies":        ("basic_details", "total_vacancies"),
    "total vacancy":          ("basic_details", "total_vacancies"),
    "application mode":       ("basic_details", "application_mode"),
    "apply mode":             ("basic_details", "application_mode"),
    "job type":               ("basic_details", "job_type"),
    "official website":       ("basic_details", "official_website"),
    # Salary
    "salary":                 ("salary_details", "pay_scale"),
    "pay scale":              ("salary_details", "pay_scale"),
    "pay band":               ("salary_details", "pay_scale"),
    "stipend":                ("salary_details", "pay_scale"),
    "remuneration":           ("salary_details", "pay_scale"),
    # Dates
    "last date":              ("important_dates", "last_date_to_apply"),
    "closing date":           ("important_dates", "last_date_to_apply"),
    "last date to apply":     ("important_dates", "last_date_to_apply"),
    "start date":             ("important_dates", "start_date"),
    "starting date":          ("important_dates", "start_date"),
    "start date for online applications": ("important_dates", "start_date"),
    "last date for online applications":  ("important_dates", "last_date_to_apply"),
    "walk-in date":           ("important_dates", "walk_in_date"),
    "walk-in interview":      ("important_dates", "walk_in_date"),
    "notification date":      ("important_dates", "notification_date"),
    "advt date":              ("important_dates", "notification_date"),
    # Qualification
    "qualification":          ("qualification", "education_qualification"),
    "educational qualification": ("qualification", "education_qualification"),
    "eligibility":            ("qualification", "education_qualification"),
    # Age
    "age limit":              ("age_limit", "age_details"),
    "age":                    ("age_limit", "age_details"),
    "maximum age":            ("age_limit", "age_details"),
    # Fee
    "application fee":        ("application_fee", "general_fee"),
    "exam fee":               ("application_fee", "general_fee"),
    "fee":                    ("application_fee", "general_fee"),
    # Selection
    "selection process":      ("selection_process", None),
    "selection mode":         ("selection_process", None),
}

# ── Section heading keywords ─────────────────────────────────
_SECTION_HEADINGS = {
    "important_dates":   ["important date", "key date", "schedule", "event date"],
    "application_fee":   ["application fee", "exam fee", "fee detail"],
    "age_limit":         ["age limit", "age relaxation"],
    "vacancy_details":   ["vacancy detail", "post detail", "vacancy distribution",
                          "post wise", "category wise", "vacancies"],
    "selection_process": ["selection process", "selection mode", "selection procedure"],
    "how_to_apply":      ["how to apply", "application process", "how to fill"],
    "important_links":   ["important link", "useful link", "apply link"],
    "faq":               ["faq", "frequently asked"],
}

def _fja_section_type(heading_text: str) -> str | None:
    """Return section type for a heading, or None."""
    ht = heading_text.lower().strip()
    for sec, kws in _SECTION_HEADINGS.items():
        if any(kw in ht for kw in kws):
            return sec
    return None


def _fja_parse_overview_table(table, detail: dict):
    """
    FJA Overview/key-value table parse karo.
    2-column rows: key | value
    """
    for row in table.find_all("tr"):
        cols = row.find_all(["td", "th"])
        if len(cols) < 2:
            continue
        raw_key = state_clean_text(cols[0].get_text()).lower().rstrip(":")
        raw_val = state_clean_text(cols[1].get_text())
        if not raw_key or not raw_val:
            continue

        mapping = _FJA_OVERVIEW_KEY_MAP.get(raw_key)
        if mapping:
            section, field = mapping
            if section == "selection_process":
                if raw_val and not _is_selection_noise(raw_val) and raw_val not in detail["selection_process"]:
                    detail["selection_process"].append(raw_val)
            elif field:
                if not detail[section].get(field):
                    detail[section][field] = raw_val
        # Even if not in map — try partial match for common fields
        else:
            for map_key, (section, field) in _FJA_OVERVIEW_KEY_MAP.items():
                if map_key in raw_key and field and not detail[section].get(field):
                    detail[section][field] = raw_val
                    break


def _fja_parse_dates_table(table, detail: dict):
    """
    Important Dates section ki table parse karo.
    Rows: Event | Date
    """
    rows = table.find_all("tr")
    # Skip header row
    for row in rows[1:] if len(rows) > 1 else rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 2:
            continue
        event = state_clean_text(cols[0].get_text()).lower()
        date_val = state_clean_text(cols[1].get_text())
        if not event or not date_val:
            continue
        if "start" in event or "begin" in event or "opening" in event:
            detail["important_dates"].setdefault("start_date", date_val)
        elif "last" in event or "closing" in event or "end date" in event:
            detail["important_dates"].setdefault("last_date_to_apply", date_val)
        elif "walk" in event or "interview" in event:
            detail["important_dates"].setdefault("walk_in_date", date_val)
        elif "exam" in event or "written" in event or "test" in event:
            detail["important_dates"].setdefault("exam_date", date_val)
        elif "result" in event:
            detail["important_dates"].setdefault("result_date", date_val)
        elif "admit" in event or "hall ticket" in event:
            detail["important_dates"].setdefault("admit_card_date", date_val)
        elif "notification" in event or "advt" in event:
            detail["important_dates"].setdefault("notification_date", date_val)
        elif "document" in event or "verification" in event:
            detail["important_dates"].setdefault("document_verification_date", date_val)
        else:
            # Generic — store as-is
            key = event.strip().replace(" ", "_").replace("/", "_")[:40]
            detail["important_dates"].setdefault(key, date_val)


def _fja_parse_fee_table(table, detail: dict):
    """Application fee table parse karo."""
    for row in table.find_all("tr"):
        cols = row.find_all(["td", "th"])
        if len(cols) < 2:
            continue
        cat = state_clean_text(cols[0].get_text()).lower()
        fee = state_clean_text(cols[1].get_text())
        if not fee:
            continue
        if "general" in cat or "obc" in cat or "ewi" in cat or "ews" in cat:
            detail["application_fee"].setdefault("general_obc_fee", fee)
        elif "sc" in cat or "st" in cat or "pwd" in cat or "pwbd" in cat or "female" in cat or "women" in cat:
            detail["application_fee"].setdefault("sc_st_pwd_fee", fee)
        elif "nil" in fee.lower() or "exempt" in fee.lower():
            detail["application_fee"].setdefault("exempted_categories", cat)
        else:
            key = cat.strip().replace(" ", "_")[:30] or "fee"
            detail["application_fee"].setdefault(key, fee)


def _fja_parse_vacancy_table(table, detail: dict):
    """
    Vacancy/post-wise table parse karo.
    Multi-column ya 2-column dono handle karo.
    """
    rows = table.find_all("tr")
    if not rows:
        return
    # Header row nikalo
    header_cols = rows[0].find_all(["th", "td"])
    headers_text = [state_clean_text(c.get_text()).lower() for c in header_cols]

    for row in rows[1:]:
        cols = row.find_all(["td", "th"])
        if not cols:
            continue
        if len(cols) == len(headers_text) and len(headers_text) > 1:
            row_dict = {}
            for i, hdr in enumerate(headers_text):
                row_dict[hdr] = state_clean_text(cols[i].get_text())
            if any(row_dict.values()):
                detail["vacancy_details"].append(row_dict)
        elif len(cols) >= 2:
            key = state_clean_text(cols[0].get_text())
            val = state_clean_text(cols[1].get_text())
            if key and val:
                detail["vacancy_details"].append({"post": key, "vacancies": val})


def _fja_parse_links_section(container, detail: dict) -> tuple[list, str | None, str | None]:
    """
    Important Links section se valid external links nikalo.
    Returns (valid_links, notification_pdf, official_url)
    """
    valid_links = []
    notification_pdf = None
    official_url = None

    for a in container.find_all("a", href=True):
        href = a["href"].strip()
        link_text = state_clean_text(a.get_text()).lower()

        if not state_is_valid_link(href):
            continue

        # Deduplicate
        if href not in valid_links:
            valid_links.append(href)

        # PDF notification
        if ".pdf" in href.lower() and not notification_pdf:
            notification_pdf = href

        # Best "apply / official" URL
        if not official_url and any(kw in link_text for kw in [
            "apply online", "official website", "apply here",
            "official site", "apply now", "apply link",
            "official notification", "download notification",
        ]):
            official_url = href

    return valid_links, notification_pdf, official_url


def scrape_job_detail(job_url, headers):
    """
    FJA article page scrape karo — properly structured extraction.
    Pages like /articles/xyz follow a standard layout:
      H1 title → meta description → Overview table (key|value)
      → Section headings (H2/H3) → Dates table, Fee table,
        Vacancy table, Links list, FAQ, How-to-apply
    """
    try:
        response = requests.get(job_url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")

        detail = {
            "basic_details":          {},
            "important_dates":        {},
            "application_fee":        {},
            "age_limit":              {},
            "qualification":          {},
            "vacancy_details":        [],
            "category_wise_vacancy":  {},
            "salary_details":         {},
            "selection_process":      [],
            "exam_pattern":           {},
            "syllabus":               {},
            "physical_eligibility":   {},
            "how_to_apply":           [],
            "important_instructions": [],
            "important_links":        {},
            "faq":                    [],
            "seo_tags":               [],
        }

        # ── 1. TITLE ───────────────────────────────────────────
        title_tag = soup.find("h1") or soup.find("h2")
        if title_tag:
            detail["basic_details"]["job_title"] = state_clean_text(title_tag.get_text())

        # ── 2. META DESCRIPTION (short info) ──────────────────
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            detail["basic_details"]["short_information"] = state_clean_text(meta_desc["content"])

        # ── 3. SEO TAGS ────────────────────────────────────────
        meta_kw = soup.find("meta", {"name": "keywords"})
        if meta_kw and meta_kw.get("content"):
            detail["seo_tags"] = [k.strip() for k in meta_kw["content"].split(",") if k.strip()]
        if not detail["seo_tags"]:
            pg_title = soup.find("title")
            if pg_title:
                detail["seo_tags"].append(state_clean_text(pg_title.get_text()))

        # ── 4. SECTION-AWARE PARSING ───────────────────────────
        # Walk through all block-level elements in document order.
        # Track current section context based on headings.

        all_elems = soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "table", "ul", "ol", "p"]
        )

        current_section = None      # e.g. "important_dates", "how_to_apply" …
        all_valid_links  = []
        notification_pdf = None
        official_url     = None
        overview_parsed  = False

        for elem in all_elems:

            tag = elem.name

            # ── Heading → update section context ──────────────
            if tag in ("h1", "h2", "h3", "h4", "h5"):
                heading = state_clean_text(elem.get_text())
                sec = _fja_section_type(heading)
                if sec:
                    current_section = sec
                continue

            # ── TABLE ─────────────────────────────────────────
            if tag == "table":
                rows = elem.find_all("tr")
                if not rows:
                    continue

                # Detect table type by first row content
                first_cols = rows[0].find_all(["th", "td"])
                first_text = " ".join(
                    state_clean_text(c.get_text()).lower() for c in first_cols
                )

                # Overview / key-value table (2 cols, first col is a label)
                if (not overview_parsed
                        and len(first_cols) == 2
                        and not any(kw in first_text for kw in
                                    ["post", "category", "ur ", "obc", "total"])):
                    _fja_parse_overview_table(elem, detail)
                    overview_parsed = True

                elif (current_section == "important_dates"
                      or any(kw in first_text for kw in ["event", "date", "schedule"])):
                    _fja_parse_dates_table(elem, detail)

                elif (current_section == "application_fee"
                      or any(kw in first_text for kw in ["fee", "category", "examination fee"])):
                    _fja_parse_fee_table(elem, detail)

                elif (current_section == "vacancy_details"
                      or any(kw in first_text for kw in
                             ["post", "vacancy", "sl.", "sl no", "post code",
                              "ur", "obc", "total", "category"])):
                    _fja_parse_vacancy_table(elem, detail)

                else:
                    # Fallback: try overview parse (may be a missed key-value table)
                    if len(first_cols) == 2 and not overview_parsed:
                        _fja_parse_overview_table(elem, detail)
                        overview_parsed = True

                # Always scan for links inside tables
                lnks, pdf, off = _fja_parse_links_section(elem, detail)
                for l in lnks:
                    if l not in all_valid_links:
                        all_valid_links.append(l)
                if pdf and not notification_pdf:
                    notification_pdf = pdf
                if off and not official_url:
                    official_url = off
                continue

            # ── UL / OL ───────────────────────────────────────
            if tag in ("ul", "ol"):
                if current_section == "how_to_apply":
                    for li in elem.find_all("li"):
                        step = state_clean_text(li.get_text())
                        # Noise filter: sidebar/nav content reject karo
                        if step and not _is_selection_noise(step) and step not in detail["how_to_apply"]:
                            detail["how_to_apply"].append(step)
                elif current_section == "selection_process":
                    for li in elem.find_all("li"):
                        step = state_clean_text(li.get_text())
                        # Noise filter: sidebar/nav content reject karo
                        if step and not _is_selection_noise(step) and step not in detail["selection_process"]:
                            detail["selection_process"].append(step)
                elif current_section == "important_links":
                    lnks, pdf, off = _fja_parse_links_section(elem, detail)
                    for l in lnks:
                        if l not in all_valid_links:
                            all_valid_links.append(l)
                    if pdf and not notification_pdf:
                        notification_pdf = pdf
                    if off and not official_url:
                        official_url = off
                else:
                    # Always scan lists for links
                    lnks, pdf, off = _fja_parse_links_section(elem, detail)
                    for l in lnks:
                        if l not in all_valid_links:
                            all_valid_links.append(l)
                    if pdf and not notification_pdf:
                        notification_pdf = pdf
                    if off and not official_url:
                        official_url = off
                continue

            # ── P / other ─────────────────────────────────────
            if tag == "p":
                lnks, pdf, off = _fja_parse_links_section(elem, detail)
                for l in lnks:
                    if l not in all_valid_links:
                        all_valid_links.append(l)
                if pdf and not notification_pdf:
                    notification_pdf = pdf
                if off and not official_url:
                    official_url = off

        # ── 5. FAQ (dedicated pass) ────────────────────────────────────
        # Strategy A: <section class="faq-section"> structure
        #   (freejobalert state_jobs pages)
        #   <section class="faq-section">
        #     <h2 class="faq-heading">...</h2>
        #     <div class="faq-container">
        #       <div class="faq-item">
        #         <h3 class="faq-question">Q1. Question?</h3>
        #         <div class="faq-answer">Answer text.</div>
        #       </div>
        #       ...
        #     </div>
        #   </section>
        faq_section = soup.find("section", class_="faq-section")
        if faq_section:
            for item in faq_section.find_all("div", class_="faq-item"):
                q_tag = item.find("h3", class_="faq-question") or item.find("h3")
                a_tag = item.find("div", class_="faq-answer") or item.find("div")
                if q_tag:
                    question = state_clean_text(q_tag.get_text())
                    # Q1. / Q2. prefix hatao
                    question = re.sub(r'^Q\d+\.?\s*', '', question).strip()
                    answer   = state_clean_text(a_tag.get_text()) if a_tag else ""
                    if question and answer:
                        detail["faq"].append({"question": question, "answer": answer})

        # Strategy B: JSON-LD FAQPage schema
        if not detail["faq"]:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    import json as _json
                    ld = _json.loads(script.string or "")
                    if isinstance(ld, dict) and ld.get("@type") == "FAQPage":
                        for entity in ld.get("mainEntity", []):
                            q_text = entity.get("name", "")
                            a_text = entity.get("acceptedAnswer", {}).get("text", "")
                            a_text = re.sub(r'<[^>]+>', '', a_text)  # strip HTML
                            if q_text and a_text:
                                detail["faq"].append({
                                    "question": state_clean_text(q_text),
                                    "answer":   state_clean_text(a_text),
                                })
                except Exception:
                    pass

        # Strategy C: Generic heading-based search (fallback)
        if not detail["faq"]:
            for tag in soup.find_all(["h2", "h3", "h4"]):
                tag_text = state_clean_text(tag.get_text()).lower()
                if "faq" in tag_text or "frequently" in tag_text:
                    sib = tag.find_next_sibling()
                    while sib:
                        q_tag = sib.find(["strong", "b", "h5", "h6"])
                        if q_tag:
                            question = state_clean_text(q_tag.get_text())
                            question = re.sub(r'^Q\d+\.?\s*', '', question).strip()
                            ans_tag  = q_tag.find_next(["p", "li"])
                            answer   = state_clean_text(ans_tag.get_text()) if ans_tag else ""
                            if question and answer:
                                detail["faq"].append({"question": question, "answer": answer})
                        sib = sib.find_next_sibling()
                        if sib and sib.name in ("h2", "h3"):
                            break

        # ── 6. HOW TO APPLY — heading+next search (fallback) ──
        if not detail["how_to_apply"]:
            for tag in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
                text = state_clean_text(tag.get_text()).lower()
                if "how to apply" in text or "application process" in text:
                    nxt = tag.find_next(["ul", "ol", "p"])
                    if nxt:
                        if nxt.name in ("ul", "ol"):
                            for li in nxt.find_all("li"):
                                step = state_clean_text(li.get_text())
                                # Noise filter
                                if step and not _is_selection_noise(step):
                                    detail["how_to_apply"].append(step)
                        else:
                            step = state_clean_text(nxt.get_text())
                            if step and not _is_selection_noise(step):
                                detail["how_to_apply"].append(step)
                    break

        # ── 6b. WHOLE-PAGE FALLBACK LINK SCAN ──────────────────
        # Section-aware walk kabhi-kabhi links miss kar deta hai (jab links
        # <li><strong><a> me hote hain ya heading match nahi hoti). Isliye
        # poore content area se saare official <a> bhi scan karo — taaki
        # koi official/PDF link miss na ho (a-to-z official links).
        content_area = (soup.find("div", class_="entry-content")
                        or soup.find("article")
                        or soup.find("main")
                        or soup.find("div", id="content")
                        or soup)
        for a in content_area.find_all("a", href=True):
            href = a["href"].strip()
            if not href.startswith("http"):
                continue
            href = href.split("#")[0]
            if state_is_valid_link(href) and href not in all_valid_links:
                all_valid_links.append(href)
                if ".pdf" in href.lower() and not notification_pdf:
                    notification_pdf = href
                low_t = state_clean_text(a.get_text()).lower()
                if not official_url and (".pdf" not in href.lower()) and \
                   any(w in low_t for w in ["official", "website", "home"]):
                    official_url = href

        # ── 7. Finalize links ──────────────────────────────────
        # Fallback for official_url: first non-pdf valid link
        if not official_url:
            non_pdf = [l for l in all_valid_links if ".pdf" not in l.lower()]
            if non_pdf:
                official_url = non_pdf[0]

        # Deduplicate, keep all official links (a-to-z) — cap 25 safety
        all_valid_links = list(dict.fromkeys(all_valid_links))[:25]

        if all_valid_links:
            detail["important_links"]["click_here"] = all_valid_links
        if notification_pdf:
            detail["important_links"]["notification_pdf"] = notification_pdf

        # Store for process_job_row
        detail["_official_url"] = official_url or ""

        return detail

    except Exception as e:
        print(f"  DETAIL ERROR [{job_url}]: {e}")
        return {}


# =====================================
# PROCESS ONE JOB ROW (called in thread)
# =====================================

def process_job_row(args):
    state_name, cols, headers = args

    try:
        post_date     = state_clean_text(cols[0].get_text())
        board         = state_clean_text(cols[1].get_text())
        post_name     = state_clean_text(cols[2].get_text())
        qualification = state_clean_text(cols[3].get_text())
        advt_no       = state_clean_text(cols[4].get_text())
        last_date     = state_clean_text(cols[5].get_text())

        link_tag = cols[6].find("a", href=True)
        if not link_tag:
            return None

        job_link = link_tag["href"].strip()
        if job_link.startswith("/"):
            job_link = "https://www.freejobalert.com" + job_link

        print(f"  → [{state_name}] {board} – {post_name}")

        job_detail = scrape_job_detail(job_link, headers)

        # Fill missing fields from list-level data
        bd = job_detail.setdefault("basic_details", {})
        if not bd.get("post_name"):         bd["post_name"]         = post_name
        if not bd.get("organization_name"): bd["organization_name"] = board
        bd["post_date"] = post_date
        bd["advt_no"]   = advt_no

        id_ = job_detail.setdefault("important_dates", {})
        if not id_.get("last_date_to_apply"): id_["last_date_to_apply"] = last_date

        q_ = job_detail.setdefault("qualification", {})
        if not q_.get("education_qualification"): q_["education_qualification"] = qualification

        # Use ONLY official URL from job detail page — never freejobalert article link
        official_url = job_detail.pop("_official_url", "") or ""

        item = {
            "name": f"{board} – {post_name}",
            "url": official_url,
            "_scraped_from": job_link,   # INTERNAL ONLY — the freejobalert listing
                                          # URL we scraped this from; used purely to
                                          # skip re-fetching the same row next run.
                                          # Never rendered (generate_all.py / website
                                          # generators only read named fields).
            "date": f"Last Date: {last_date}",
            "lastDate": last_date,
            "qualification": qualification,
            "postDate": post_date,
            "board": board,
            "category": f"STATE WISE JOBS - {state_name}",
            "detail": job_detail
        }

        return item

    except Exception as e:
        print(f"  ROW ERROR [{state_name}]: {e}")
        return None


# =====================================
# MAIN SCRAPER
# =====================================

def scrape_state_jobs():

    # freejobalert.com retired the single combined /state-government-jobs/ page
    # (now 404). Each state/UT now has its own page: /{abbr}-government-jobs/.
    # We fetch every state page individually so the list is always FRESH.
    # freejobalert uses abbreviated per-state slugs (ap-, hp-, an-, tn- ...).
    # Some UTs are inconsistent or have no dedicated page, so each state lists
    # MULTIPLE candidate slugs — the scraper tries each until one returns 200
    # with a real job table. (Confirmed working: ap, hp, an, tn, mp, up, wb, jk.)
    STATE_URL_MAP = {
        "Andhra Pradesh":      ["ap-government-jobs", "andhra-pradesh-government-jobs"],
        "Arunachal Pradesh":   ["ar-government-jobs", "arunachal-pradesh-government-jobs"],
        "Assam":               ["as-government-jobs", "assam-government-jobs"],
        "Bihar":               ["br-government-jobs", "bihar-government-jobs"],
        "Chhattisgarh":        ["cg-government-jobs", "chhattisgarh-government-jobs"],
        "Goa":                 ["ga-government-jobs", "goa-government-jobs"],
        "Gujarat":             ["gj-government-jobs", "gujarat-government-jobs"],
        "Haryana":             ["hr-government-jobs", "haryana-government-jobs"],
        "Himachal Pradesh":    ["hp-government-jobs", "himachal-pradesh-government-jobs"],
        "Jharkhand":           ["jh-government-jobs", "jharkhand-government-jobs"],
        "Karnataka":           ["ka-government-jobs", "karnataka-government-jobs"],
        "Kerala":              ["kl-government-jobs", "kerala-government-jobs"],
        "Madhya Pradesh":      ["mp-government-jobs", "madhya-pradesh-government-jobs"],
        "Maharashtra":         ["mh-government-jobs", "maharashtra-government-jobs"],
        "Manipur":             ["mn-government-jobs", "manipur-government-jobs"],
        "Meghalaya":           ["ml-government-jobs", "meghalaya-government-jobs"],
        "Mizoram":             ["mz-government-jobs", "mizoram-government-jobs"],
        "Nagaland":            ["nl-government-jobs", "nagaland-government-jobs"],
        "Odisha":              ["od-government-jobs", "or-government-jobs", "odisha-government-jobs"],
        "Punjab":              ["pb-government-jobs", "punjab-government-jobs"],
        "Rajasthan":           ["rj-government-jobs", "rajasthan-government-jobs"],
        "Sikkim":              ["sk-government-jobs", "sikkim-government-jobs"],
        "Tamil Nadu":          ["tn-government-jobs", "tamil-nadu-government-jobs"],
        "Telangana":           ["tg-government-jobs", "ts-government-jobs", "telangana-government-jobs"],
        "Tripura":             ["tr-government-jobs", "tripura-government-jobs"],
        "Uttar Pradesh":       ["up-government-jobs", "uttar-pradesh-government-jobs"],
        "Uttarakhand":         ["uk-government-jobs", "ua-government-jobs", "uttarakhand-government-jobs"],
        "West Bengal":         ["wb-government-jobs", "west-bengal-government-jobs"],
        "Delhi":               ["dl-government-jobs", "delhi-government-jobs"],
        "Jammu and Kashmir":   ["jk-government-jobs", "jammu-and-kashmir-government-jobs"],
        "Chandigarh":          ["ch-government-jobs", "chandigarh-government-jobs"],
        "Puducherry":          ["py-government-jobs", "pondicherry-government-jobs", "puducherry-government-jobs"],
        "Andaman and Nicobar": ["an-government-jobs", "andaman-and-nicobar-government-jobs"],
        "Dadra and Nagar Haveli": ["dn-government-jobs", "dh-government-jobs", "dadra-and-nagar-haveli-government-jobs"],
        "Daman and Diu":       ["dd-government-jobs", "dm-government-jobs", "daman-and-diu-government-jobs"],
        "Lakshadweep":         ["ld-government-jobs", "lakshadweep-government-jobs"],
        "Ladakh":              ["la-government-jobs", "ladakh-government-jobs"],
    }
    BASE = "https://www.freejobalert.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Referer":         "https://www.google.com/",
    }

    final_json = {"sections": []}
    all_jobs = []           # list of (state_name, cols)
    fetched_states = []     # states whose page loaded OK (200 + table found)
    failed_states = []      # states whose page 404'd / errored

    # ── Fetch each state page, collect job rows ───────────────────
    for state_name, slugs in STATE_URL_MAP.items():
        # Each state has a list of candidate slugs — try them until one works.
        slug_list = slugs if isinstance(slugs, list) else [slugs]
        rows_added = 0
        used_url = ""
        last_status = None
        for slug in slug_list:
            url = BASE + slug + "/"
            # Small UT pages on freejobalert are flaky (intermittent 404/500/empty),
            # so retry each candidate slug a few times before giving up on it.
            cand_rows = 0
            cand_jobs = []
            for attempt in range(3):
                try:
                    response = requests.get(url, headers=headers, timeout=30)
                    last_status = response.status_code
                    if response.status_code != 200:
                        time.sleep(1.0)  # transient error — wait and retry
                        continue
                    soup = BeautifulSoup(response.text, "html.parser")
                    tables = soup.find_all("table")
                    if not tables:
                        time.sleep(1.0)
                        continue
                    cand_rows = 0
                    cand_jobs = []
                    for table in tables:
                        rows = table.find_all("tr")
                        if len(rows) <= 1:
                            continue
                        for row in rows[1:]:
                            cols = row.find_all("td")
                            if len(cols) >= 7:
                                cand_jobs.append((state_name, cols))
                                cand_rows += 1
                    if cand_rows:
                        break  # got data on this attempt — stop retrying
                    time.sleep(1.0)  # 200 but no rows — retry once more
                except Exception as e:
                    print(f"  [ERR]  {state_name} ({slug}) attempt {attempt+1}: {e}")
                    time.sleep(1.0)
            if cand_rows:
                all_jobs.extend(cand_jobs)
                rows_added = cand_rows
                used_url = url
                break  # found a working slug — stop trying other candidates
            time.sleep(0.3)  # polite delay between candidate slugs

        if rows_added:
            fetched_states.append(state_name)
            print(f"  [OK]   {state_name}: {rows_added} rows  ({used_url})")
        else:
            failed_states.append(state_name)
            _why = f"HTTP {last_status}" if last_status and last_status != 200 else "no jobs on any candidate URL"
            print(f"  [SKIP] {state_name}: {_why}")

        time.sleep(0.4)  # be polite to the source

    print(f"\nTOTAL JOBS TO SCRAPE: {len(all_jobs)} "
          f"(from {len(fetched_states)} states, {len(failed_states)} failed)")

    # ── SAFETY: if nothing fetched, DON'T overwrite the existing JSON ──
    if not all_jobs:
        print("\n[ABORT] No state jobs fetched from any URL — keeping the EXISTING "
              "State_Wise_Jobs.json untouched (no stale-overwrite, no data loss).")
        print("        Check whether freejobalert.com changed its URL structure again.")
        return

    # ── INCREMENTAL SCRAPE: load whatever we already have, so we only hit the
    # detail page for rows that are genuinely new. Same "skip what's already
    # scraped" pattern used across the other scrapers — cuts state-wise
    # requests from "every row, every run" down to just new postings. ──
    _existing_items_by_state = {}
    if os.path.exists("State_Wise_Jobs.json"):
        try:
            with open("State_Wise_Jobs.json", encoding="utf-8") as _f:
                _prev = json.load(_f)
            for _sec in _prev.get("sections", []):
                _existing_items_by_state[_sec.get("state", "")] = _sec.get("items", [])
        except Exception as _e:
            print(f"  [INCREMENTAL] could not load previous State_Wise_Jobs.json: {_e}")

    def _row_job_link(cols):
        """Cheaply pull just the detail-page URL out of a table row, without
        doing a full process_job_row() (which makes the expensive request)."""
        try:
            link_tag = cols[6].find("a", href=True)
            if not link_tag:
                return ""
            jl = link_tag["href"].strip()
            if jl.startswith("/"):
                jl = "https://www.freejobalert.com" + jl
            return jl
        except Exception:
            return ""

    # split all_jobs into already-scraped (carry forward) vs genuinely new
    _carry_forward_items = {}   # state_name -> [item, ...]
    _new_all_jobs = []
    _skipped_count = 0
    for state_name, cols in all_jobs:
        _existing_urls = {it.get("_scraped_from", "") for it in
                          _existing_items_by_state.get(state_name, []) if it.get("_scraped_from")}
        _existing_by_url = {it["_scraped_from"]: it for it in
                            _existing_items_by_state.get(state_name, []) if it.get("_scraped_from")}
        _link = _row_job_link(cols)
        if _link and _link in _existing_urls:
            _carry_forward_items.setdefault(state_name, []).append(_existing_by_url[_link])
            _skipped_count += 1
        else:
            _new_all_jobs.append((state_name, cols))
    print(f"\n[INCREMENTAL] {_skipped_count} rows already scraped (skipped), "
          f"{len(_new_all_jobs)} new rows to fetch")
    all_jobs = _new_all_jobs

    # ── Parallel scraping of each job's detail page ───────────────
    state_items = {}        # state_name -> [items]
    # seed with carried-forward (already-scraped) items first
    for _st, _items in _carry_forward_items.items():
        state_items.setdefault(_st, []).extend(_items)
    args_list = [(state, cols, headers) for state, cols in all_jobs]

    # Scrape in parallel but PRESERVE original site order: store each result at
    # its original index, then assemble in order. (as_completed returns in random
    # completion order which scrambled the per-state job sequence.)
    results_by_idx = [None] * len(args_list)
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_job_row, args): idx
                   for idx, args in enumerate(args_list)}
        for future in as_completed(futures):
            idx = futures[future]
            state_name = args_list[idx][0]
            try:
                item = future.result()
                if item:
                    results_by_idx[idx] = item
            except Exception as e:
                print(f"FUTURE ERROR [{state_name}]: {e}")

    # Re-assemble in original order
    for idx, args in enumerate(args_list):
        item = results_by_idx[idx]
        if item:
            state_name = args[0]
            state_items.setdefault(state_name, []).append(item)

    # ── Build sections in original (map) order ────────────────────
    # IMPORTANT: must include states that had ZERO new rows (fully carried
    # forward from the incremental skip above) — otherwise those states'
    # sections would silently disappear from the output.
    seen_states = []
    for state_name in STATE_URL_MAP.keys():
        if state_name in state_items and state_name not in seen_states:
            seen_states.append(state_name)

    for state_name in seen_states:
        items = state_items.get(state_name, [])
        if items:
            final_json["sections"].append({
                "id":       state_create_id(state_name),
                "title":    f"{state_name} Govt Jobs 2026",
                "category": f"STATE WISE JOBS - {state_name}",
                "state":    state_name,
                "items":    items
            })

    # ── SAFETY: never write an empty sections file over good data ──
    if not final_json["sections"]:
        print("\n[ABORT] Parsed 0 sections after detail scrape — keeping EXISTING JSON.")
        return

    # ── Save JSON ──────────────────────────────────
    with open("State_Wise_Jobs.json", "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=4, ensure_ascii=False)

    total_jobs = sum(len(s["items"]) for s in final_json["sections"])

    print("\n===================================")
    print("STATE WISE SCRAPING SUCCESS")
    print(f"TOTAL STATES : {len(final_json['sections'])}")
    print(f"TOTAL JOBS   : {total_jobs}")
    print("JSON FILE    : State_Wise_Jobs.json")
    print("===================================")


# =====================================
# RUN
# =====================================


# ================================================================


# ================================================================
# MERGE INTO UNIFIED JSON
# ================================================================
if __name__ == "__main__":
    from scraper_merge import merge_into_json, wait_for_internet
    import json as _json_mod, os

    wait_for_internet("State Jobs")

    print("\n" + "="*60)
    print("  SCRAPER: State Govt Jobs")
    print("="*60)

    error_str = ""
    try:
        scrape_state_jobs()   # saves to State_Wise_Jobs.json
    except Exception as e:
        import traceback; traceback.print_exc()
        error_str = str(e)

    scraped = {}
    if os.path.exists("State_Wise_Jobs.json"):
        with open("State_Wise_Jobs.json", encoding="utf-8") as f:
            scraped = _json_mod.load(f)

    merge_into_json(
        source        = "state_jobs",
        fresh_data    = scraped,
        scraper_error = error_str,
    )
