#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================================
# SHARED PARSE HELPERS - fja_parse_helpers.py
# ================================================================
# FreeJobAlert-family scrapers (qualification / state / district) ke liye
# common parsing helpers. Yahan 4 bug-classes ke fixes centralised hain,
# taaki teeno scrapers ka behaviour guaranteed identical rahe:
#
#   Bug 1 - Multi-table "khichdi" (company/category/PwD tables ek flat
#           array me mix ho jaate the)          -> isolate_vacancy_tables()
#   Bug 2 - Toote/galat links (relative + deep subdomain URLs base pe glue
#           ho jaate the, labels blank/junk)    -> resolve_href(), cap_label()
#   Bug 3 - Khaali age_limit / syllabus {} (jab data <p>/<ul> me tha, table
#           me nahi)                            -> extract_section_text()
#   Bug 4 - Ad / "DON'T MISS" recommendation text qualification/eligibility
#           me leak ho jaata tha                -> sanitize_dom(), is_ad_text()
#
# Sab pure functions hain - na network, na global state - isliye teeno
# scrapers import karke reuse kar sakte hain.
# ================================================================

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse


# ============================================================
# EXTENDED / REVISED DATES  (date-extension capture)
# ============================================================
# Source sites often ADD a row like "Extended Last Date for Online Application"
# ABOVE/BELOW the original "Last Date" row. The generic 'last date' mapping would
# either swallow it (first-wins) or drop it — so the new deadline never showed.
# This classifier routes any extension/revision/postponement label to its OWN
# important_dates field, so it is always captured AND rendered as a distinct row.
# NOTE: prefix match (no trailing \b) so 'extend' also matches extended/extension,
# 'revis' -> revised/revision, 'postpon' -> postponed, 'reschedul' -> rescheduled.
_EXTEND_DATE_RE = re.compile(
    r"\b(extend|extn|revis|re-?schedul|postpon|re-?open|reopen|"
    r"new\s+last|new\s+closing|further\s+extend)", re.IGNORECASE)


def extended_date_field(raw_key):
    """Return the distinct important_dates field for an EXTENDED/revised date
    label (e.g. 'Extended Last Date' -> 'extended_last_date'), else '' for a
    normal date. Sub-types (exam/admit/interview/fee/correction) get their own
    'revised_*'/'extended_*' key so nothing collides."""
    k = (raw_key or "").lower()
    if not _EXTEND_DATE_RE.search(k):
        return ""
    if "exam" in k:                                return "revised_exam_date"
    if "admit" in k or "hall" in k:                return "revised_admit_card_date"
    if "interview" in k:                           return "revised_interview_date"
    if "fee" in k or "payment" in k:               return "extended_fee_payment_date"
    if "correction" in k or "edit" in k:           return "extended_correction_date"
    return "extended_last_date"


def assign_important_date(important_dates: dict, raw_key: str, val: str, date_map: dict) -> bool:
    """Single place that decides where a date row goes. Returns True if handled.

    Order:
      1. EXTENSION/revision label  -> its own field (latest value always wins).
      2. Known label in `date_map` -> canonical field (first non-empty wins).
      3. Unknown label             -> stored verbatim (nothing is ever lost).
    """
    if not val:
        return False
    key = (raw_key or "").lower().rstrip(":").strip()
    ext = extended_date_field(key)
    if ext:
        important_dates[ext] = val          # a re-scrape must reflect the newest extension
        return True
    for map_key, field in date_map.items():
        if map_key in key:
            if not important_dates.get(field):
                important_dates[field] = val
            return True
    important_dates[key] = val              # keep any unmapped date as-is
    return True


# ============================================================
# RE-SCRAPE-ON-UPDATE  (refresh policy)
# ============================================================
# The incremental cache used to skip an already-scraped URL FOREVER, so when a
# source page changed (date extended, corrigendum, extra vacancy) the update was
# never captured. `needs_refresh()` fixes that: an ACTIVE job (deadline not yet
# past) is re-fetched at most once per `refresh_hours`; an EXPIRED job is never
# re-fetched. Bounds requests to the small set of live jobs, not the whole 5000.
_DMY = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b")
_YMD = re.compile(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b")
_DMONY = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")
_MONDY = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b")
_MONTHS = {m[:3].lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}


def parse_date_loose(s):
    """Best-effort date parse from messy strings ('09-07-2026 (04:00 PM)',
    '20 July 2026', 'Jul 3, 2026', '2026-07-06'). Returns date or None."""
    if not s:
        return None
    s = str(s)
    m = _YMD.search(s)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = _DMY.search(s)
        if m:
            d, mo, y = map(int, m.groups())
        else:
            m = _DMONY.search(s)
            if m:
                d = int(m.group(1)); mo = _MONTHS.get(m.group(2)[:3].lower(), 0); y = int(m.group(3))
            else:
                m = _MONDY.search(s)
                if not m:
                    return None
                mo = _MONTHS.get(m.group(1)[:3].lower(), 0); d = int(m.group(2)); y = int(m.group(3))
    try:
        return datetime(y, mo, d).date()
    except ValueError:
        return None


# Deadline field names across every scraper schema (snake_case FJA + camelCase
# SarkariResult/Network + a few one-off variants). Extended keys come first.
_LAST_DATE_KEYS = ("extended_last_date", "date_extended", "extendedLastDate",
                   "last_date_to_apply", "lastDateApplyOnline", "lastDateToApply",
                   "last_date", "lastDate", "application_last_date",
                   "fee_payment_last_date", "extended_fee_payment_date",
                   "feePaymentLastDate", "exam_date", "examDate")
# Sub-dicts that may hold the dates, in any schema.
_DATE_DICT_KEYS = ("important_dates", "importantDates")


def _iter_date_dicts(item):
    for dk in _DATE_DICT_KEYS:
        v = item.get(dk)
        if isinstance(v, dict):
            yield v
    _d = item.get("detail")
    if isinstance(_d, dict):
        for dk in _DATE_DICT_KEYS:
            v = _d.get(dk)
            if isinstance(v, dict):
                yield v


def job_effective_last_date(item: dict):
    """Latest meaningful deadline for a job (prefers extended over original).
    Schema-agnostic: flat or nested 'detail', snake_case or camelCase, plus a
    plain 'date'/'last_date' string ('Last Date: 09-07-2026')."""
    item = item or {}
    best = None
    for id_ in _iter_date_dicts(item):
        for k in _LAST_DATE_KEYS:
            d = parse_date_loose(id_.get(k))
            if d and (best is None or d > best):
                best = d
    for s in (item.get("date"), item.get("last_date"), item.get("lastDate")):
        d = parse_date_loose(s)
        if d and (best is None or d > best):
            best = d
    return best


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def needs_refresh(item: dict, now=None, refresh_hours: float = 20, grace_days: int = 3) -> bool:
    """True if an already-scraped job should be re-fetched to catch source
    updates. Active (deadline within grace) + not checked within refresh_hours,
    OR deadline unknown. Expired jobs return False (never re-fetched)."""
    now = now or datetime.now(timezone.utc)
    eff = job_effective_last_date(item)
    if eff is not None and eff < (now.date() - timedelta(days=grace_days)):
        return False                        # clearly expired — content won't change
    lc = (item or {}).get("_last_checked")
    if not lc:
        return True                         # never stamped -> check once
    try:
        lc_dt = datetime.fromisoformat(lc)
        if lc_dt.tzinfo is None:
            lc_dt = lc_dt.replace(tzinfo=timezone.utc)
    except Exception:
        return True
    return (now - lc_dt).total_seconds() > refresh_hours * 3600


# ============================================================
# TEXT UTIL (default clean - scraper apna clean() pass kar sakta hai)
# ============================================================
def _default_clean(x) -> str:
    if not x:
        return ""
    return " ".join(str(x).split()).strip()


# ============================================================
# JUNK-JOB GUARD (thin/empty title -> junk slug -> future 404)
# ============================================================
# Jab ek FJA page se real title extract nahi hota (ad/nav/empty page), title
# thin/khaali reh jaata hai aur slug numbers/tukdo se ban jaata hai
# (1-2026-5, 2002, page, ppp, haryana, yojana...). Aise page site pe 404 churn
# banate hain. Yeh guard scrape ke waqt hi aise job ko reject kar deta hai —
# jo site-side generate_all.is_junk_slug() ka hu-ba-hu mirror hai.
def _norm_slug(s) -> str:
    s = str(s or "").strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")[:80].strip("-")


def is_junk_slug(slug) -> bool:
    """True when a /jobs/ slug carries no real job content: the literal 'page'
    fallback, all-numeric (2002, 1-2026-5), too few letters (id, pdf, ppp), or a
    lone acronym/word + year (hssc-2026, haryana, yojana)."""
    s = _norm_slug(slug)
    if not s or s == "page":
        return True
    letters = re.sub(r"[^a-z]", "", s)
    if len(letters) < 4:
        return True
    if re.fullmatch(r"[\d\-]+", s):
        return True
    tokens = [t for t in s.split("-") if re.fullmatch(r"[a-z]{3,}", t)]
    if len(tokens) < 2 and len(letters) < 8:
        return True
    return False


def is_thin_title(title) -> bool:
    """True when a title has too little real content to be a genuine posting
    (empty, or fewer than 8 alphabetic characters)."""
    letters = re.sub(r"[^a-zA-Z]", "", str(title or ""))
    return len(letters) < 8


def is_junk_job(title, slug=None) -> bool:
    """A job is junk (skip scraping/emitting) when its title is thin AND the
    resulting slug is junk. Requiring BOTH avoids dropping a real posting that
    merely has a short slug."""
    slug = slug if slug is not None else _norm_slug(title)
    return is_thin_title(title) and is_junk_slug(slug)


# ============================================================
# BUG 4 - DOM SANITIZATION (ad / recommendation widgets)
# ============================================================
# Class-based ad / follow-bar / "DON'T MISS" recommendation slots.
AD_NOISE_SELECTORS = [
    ".fja-dontmiss", ".fja-dont-miss", ".dontmiss", ".dont-miss",
    ".cj-widget-container", ".cj-widget", ".cj-recommendation",
    ".fja-follow-bar", ".fja-follow", ".fja-mob-follow",
    ".fja-social-follow-row", ".fja-alert-widget",
    ".yarpp", ".yarpp-related", ".related-posts", ".related-articles",
    ".recommended", ".recommended-posts", ".trending", ".trending-now",
    ".outbrain", ".taboola", ".ob-widget", ".trc_related_container",
    ".ad", ".ads", ".ad_div", ".ad-container", ".advertisement",
    ".adsbygoogle", ".google-auto-placed", ".addtoany_shortcode",
    ".sharedaddy", ".video-ad-container", ".whatsapp-button-container",
    ".join-play-games-container", ".games-buttons-row",
    ".author-bio-container", ".article-social-icons",
]
# Structural tags jo kabhi useful content nahi hote.
AD_NOISE_TAGS = ["style", "noscript", "iframe", "ins"]

# Text jahan bhi recommendation/ad residue ho.
_AD_TEXT_RE = re.compile(
    r"(don'?t\s*miss|also\s*read|you\s*may\s*(also\s*)?like|"
    r"recommended\s*for\s*you|trending\s*now|sponsored|advertisement|"
    r"related\s*(posts|articles|jobs))",
    re.IGNORECASE,
)
# Jab ad phrase element ke SHURU me ho, to woh poora element recommendation hai.
_AD_TEXT_START_RE = re.compile(
    r"^\s*(don'?t\s*miss|also\s*read|recommended\s+for\s+you|"
    r"you\s*may\s*(also\s*)?like|trending\s*now|sponsored)\b",
    re.IGNORECASE,
)
_AD_INLINE_TAGS = ["a", "span", "small", "em", "strong", "b"]
_AD_BLOCK_TAGS = ["p", "li", "div", "h3", "h4", "h5", "figcaption"]


def sanitize_dom(node):
    """Ad slots, follow-bars aur 'DON'T MISS' recommendation widgets ko in-place
    destroy karo - taaki unka text kabhi qualification / eligibility fields me
    leak na kare (Bug 4). Poore soup ya kisi content sub-tree, dono par safe.

    NOTE: <script type="application/ld+json"> ko preserve karta hai - kai pages
    apna FAQ / job schema wahin rakhte hain, isliye woh delete nahi hota.
    """
    if node is None:
        return node
    # 1) Class-selector based ad blocks
    try:
        for sel in AD_NOISE_SELECTORS:
            for el in node.select(sel):
                el.decompose()
    except Exception:
        pass
    # 2) Scripts: sirf non-JSON-LD hatao (structured data survive kare)
    for tag in node.find_all("script"):
        if (tag.get("type") or "").strip().lower() == "application/ld+json":
            continue
        tag.decompose()
    for tag in node.find_all(AD_NOISE_TAGS):
        tag.decompose()
    # 3) Inline ad links/spans (e.g. <span>DON'T MISS ...</span> ek legit
    #    paragraph ke beech me) - inhe safely nikaalo.
    for tag in node.find_all(_AD_INLINE_TAGS):
        try:
            if is_ad_text(tag.get_text(" ", strip=True)):
                tag.decompose()
        except Exception:
            pass
    # 4) Standalone recommendation blocks jinki class nahi hai lekin text
    #    ad-phrase se SHURU hota hai. Nested table/list wale blocks chhod do
    #    (real content ho sakta hai).
    for tag in node.find_all(_AD_BLOCK_TAGS):
        try:
            txt = tag.get_text(" ", strip=True)
            if (txt and len(txt) < 160
                    and _AD_TEXT_START_RE.match(txt)
                    and not tag.find(["table", "ul", "ol"])):
                tag.decompose()
        except Exception:
            pass
    return node


def is_ad_text(text: str) -> bool:
    """True agar text ek recommendation/ad residue jaisa dikhta hai."""
    if not text:
        return False
    return bool(_AD_TEXT_RE.search(text))


# ============================================================
# BUG 2 - SAFE ABSOLUTE URL RESOLUTION
# ============================================================
_FILE_EXTS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "html", "htm",
    "php", "aspx", "jsp", "jpg", "jpeg", "png", "gif", "webp", "svg",
    "zip", "rar", "txt", "csv",
}
_SCHEMELESS_HOST_RE = re.compile(
    r"^(www\.)?[a-z0-9][a-z0-9\-]*(\.[a-z0-9\-]+)+", re.IGNORECASE
)


def resolve_href(base_url: str, href: str) -> str:
    """Absolute, deep-path-preserving URL resolution (Bug 2).

    Handle karta hai:
      - protocol-relative   //host/path              -> https://host/path
      - scheme-less domain  www.digitalm.com/x       -> https://www.digitalm.com/x
                            upanganwadibharti.in/reg  -> https://upanganwadibharti.in/reg
      - normal relative     /files/x , notice.pdf    -> urljoin(base, href)

    Pehle scheme-less DEEP subdomain links base ke saath glue ho jaate the
    (https://freejobalert.com/www.digitalm.com/x) - ab woh preserve hota hai.
    """
    if not href:
        return ""
    href = href.strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return href
    if href.startswith("//"):
        scheme = urlparse(base_url).scheme or "https"
        return f"{scheme}:{href}"
    if href.startswith(("http://", "https://")):
        return href
    # Root-relative ya explicit relative -> normal join
    if href.startswith(("/", "./", "../")):
        return urljoin(base_url, href)
    # Scheme-less lekin domain-jaisa? (pehla segment me dot + valid TLD)
    first_seg = href.split("/", 1)[0].split("?", 1)[0]
    if "." in first_seg and _SCHEMELESS_HOST_RE.match(first_seg):
        tld = first_seg.rsplit(".", 1)[-1].lower()
        if tld not in _FILE_EXTS and re.fullmatch(r"[a-z]{2,24}", tld):
            return "https://" + href
    return urljoin(base_url, href)


def cap_label(label: str, max_len: int = 90, fallback: str = "Official Link") -> str:
    """Label ko clean + bounded rakho. Blank ya bahut lamba (junk outer string)
    label ko sensible fallback se replace karo (Bug 2)."""
    label = (label or "").strip().strip(":").strip()
    if not label:
        return fallback
    if len(label) > max_len:
        return "Click Here / Official Link"
    return label


# ============================================================
# TABLE -> LIST-OF-DICTS MATRIX
# ============================================================
def _norm_key(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w]+", "_", text, flags=re.UNICODE)
    return text.strip("_")[:40]


def _coerce_num(val):
    """Pure integer strings ('183', '1,234') ko int me convert karo; baaki as-is."""
    if isinstance(val, str):
        s = val.strip()
        if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s) or re.fullmatch(r"-?\d+", s):
            try:
                return int(s.replace(",", ""))
            except ValueError:
                return val
    return val


def parse_table_matrix(table, clean=None):
    """HTML table ko list-of-dicts me convert karo, normalized header keys ke saath.
    Numeric count columns ko int me coerce karta hai (schema-clean output)."""
    clean = clean or _default_clean
    rows = table.find_all("tr")
    if not rows:
        return []
    header_cells = rows[0].find_all(["th", "td"])
    headers = [clean(c.get_text(" ")) for c in header_cells]
    if not any(headers):
        return []
    out = []
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        entry = {}
        for i, cell in enumerate(cells):
            raw_key = headers[i] if i < len(headers) and headers[i] else ""
            key = _norm_key(raw_key) or f"col_{i + 1}"
            if key in entry:                      # duplicate header -> suffix
                key = f"{key}_{i + 1}"
            entry[key] = _coerce_num(clean(cell.get_text(" ")))
        if any(v not in ("", None) for v in entry.values()):
            out.append(entry)
    return out


# ============================================================
# BUG 1 - MULTI-TABLE ISOLATION (company / category / PwD ...)
# ============================================================
# Header/caption keywords -> named breakdown bucket. Order matters:
# PwD tables aksar company columns bhi rakhte hain, isliye PwD pehle check hota hai.
_VAC_BUCKETS = [
    ("pwd_wise_breakdown",        ["pwbd", "pwd", "divyang", "benchmark disab",
                                   "disabilit", "physically handicap", " ph "]),
    ("company_wise_breakdown",    ["company", "discom", "utility", "unit-wise",
                                   "unit wise", "corporation"]),
    ("category_wise_breakdown",   ["category", "community", "reservation", "caste",
                                   "social", "obc", "sc/st", "ur/", "ews"]),
    ("gender_wise_breakdown",     ["gender", "male", "female", "men/women"]),
    ("discipline_wise_breakdown", ["discipline", "trade", "branch", "stream",
                                   "subject-wise", "specialization"]),
    ("post_wise_breakdown",       ["post", "position", "designation", "vacanc"]),
]
_CAPTION_TAGS = ["caption", "strong", "b", "h6", "h5", "h4", "h3", "h2"]


def _classify_vacancy_table(haystack: str) -> str:
    t = " " + (haystack or "").lower() + " "
    for bucket, kws in _VAC_BUCKETS:
        if any(kw in t for kw in kws):
            return bucket
    return "additional_breakdown"


def _looks_like_value(t: str) -> str:
    """True agar text ek data-value hai (date/number/currency) — caption nahi."""
    tl = (t or "").strip()
    if not tl:
        return True
    # Chhoti string jo mostly ek date hai (e.g. "20 July 2026") — value.
    # Lekin lambi label jisme date bracket me ho ("Age Limit (as on 1 Oct 2026)")
    # ko value mat samjho.
    if len(tl) < 25 and re.search(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b", tl):
        return True
    letters = sum(c.isalpha() for c in tl)
    digits = sum(c.isdigit() for c in tl)
    if digits >= letters or "₹" in tl or "rs." in tl.lower():
        return True
    return False


def _table_caption(table, clean) -> str:
    """Table ke context heading/caption ko dhundo - pehle <caption>, warna nearest
    preceding heading/label (jo table ke andar nahi hai, aur ek plain value nahi)."""
    cap = table.find("caption")
    if cap:
        t = clean(cap.get_text(" "))
        if t:
            return t
    hops = 0
    for prev in table.find_all_previous(_CAPTION_TAGS):
        hops += 1
        if hops > 30:
            break
        t = clean(prev.get_text(" "))
        if t and 2 < len(t) <= 140 and not _looks_like_value(t):
            return t
    return ""


def isolate_vacancy_tables(siblings, clean=None):
    """Bug 1 fix: ek section ke andar ki multiple vacancy tables ko unke header/
    caption ke hisaab se alag-alag breakdown buckets me isolate karo, taaki
    'Company: Total' aur 'Category: Total' rows aapas me collide na karein.

    siblings: elements ki list (heading ke following siblings), ya seedhe
              [table_element]. Nested (div/section ke andar) tables bhi uthata hai.
    Returns: { bucket_name: [row_dict, ...], ... }
    """
    clean = clean or _default_clean
    tables = []
    for sib in siblings:
        name = getattr(sib, "name", None)
        if name == "table":
            tables.append(sib)
        elif name in ("div", "figure", "section"):
            tables.extend(sib.find_all("table"))
    breakdown = {}
    for tbl in tables:
        rows = parse_table_matrix(tbl, clean=clean)
        if not rows:
            continue
        caption = _table_caption(tbl, clean)
        first_row = tbl.find("tr")
        header_txt = clean(first_row.get_text(" ")) if first_row else ""
        bucket = _classify_vacancy_table(f"{caption} {header_txt}")
        breakdown.setdefault(bucket, []).extend(rows)
    return breakdown


# ============================================================
# BUG 3 - HEADING-BASED TEXT EXTRACTION (age / syllabus fallback)
# ============================================================
_HEAD_TAGS = ["h2", "h3", "h4", "h5", "h6"]


def extract_section_text(content, keywords, clean=None, max_len=2500):
    """Bug 3 fix: kisi heading (h2..h6) ko keywords se match karke uske baad ke
    <p>/<ul>/<ol>/<table> text ko collect karo - jab data hard-table me nahi,
    paragraphs/lists me hota hai (jaise age relaxation ya syllabus topics).

    Ad/recommendation lines automatically drop ho jaati hain.
    Pehla matching heading jiska koi content mile, uska text return karta hai.
    """
    clean = clean or _default_clean
    kws = [k.lower() for k in keywords]
    for h in content.find_all(_HEAD_TAGS):
        htext = clean(h.get_text(" ")).lower()
        if not htext or not any(k in htext for k in kws):
            continue
        parts = []
        for sib in h.find_next_siblings():
            if getattr(sib, "name", None) in _HEAD_TAGS:
                break
            if getattr(sib, "name", None) in ("p", "ul", "ol", "div", "table"):
                t = clean(sib.get_text(" "))
                if t and not is_ad_text(t):
                    parts.append(t)
        if parts:
            joined = " | ".join(parts).strip(" |")
            if joined:
                return joined[:max_len]
    return ""


# ============================================================
# ROW DE-DUPLICATION (Bug: same table appended 2-3x)
# ============================================================
import json as _json_rowkey


def _row_key(row) -> str:
    """Stable exact-match key for a table-row dict."""
    try:
        return _json_rowkey.dumps(row, sort_keys=True, ensure_ascii=False)
    except Exception:
        return str(row)


def dedup_rows(rows):
    """Exact-duplicate row dicts hatao, order preserve karte hue."""
    out, seen = [], set()
    for r in rows or []:
        k = _row_key(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def merge_breakdown(vb: dict, breakdown: dict):
    """isolate_vacancy_tables() ka output `vb` me merge karo — har bucket me
    exact-duplicate rows skip karte hue (khichdi/triple-clone na bane)."""
    for bk, rows in (breakdown or {}).items():
        bucket = vb.setdefault(bk, [])
        seen = {_row_key(r) for r in bucket}
        for r in rows:
            k = _row_key(r)
            if k not in seen:
                seen.add(k)
                bucket.append(r)
    return vb


# ============================================================
# FAQ QUESTION VALIDATION (anti-bleeding)
# ============================================================
_Q_WORDS = {
    "what", "when", "how", "is", "are", "can", "who", "which", "why",
    "where", "whom", "does", "do", "will", "should", "did", "was",
    "were", "whose", "shall", "may", "kya", "kaise", "kab", "kaun",
    "kitni", "kitna", "kahan",
}


def looks_like_question(q: str) -> bool:
    """True agar `q` genuinely ek question hai — '?' pe khatam ho ya kisi
    question-word se shuru ho. Warna (plain table-cell / statement) reject.
    'Q6.' / '1.' jaise prefixes strip karke check hota hai."""
    q = (q or "").strip()
    if not q:
        return False
    if q.endswith("?"):
        return True
    # leading "Q6." / "1)" / "Q." prefix hatao
    stripped = re.sub(r"^\s*q?\d*[\.\)\:\-]*\s*", "", q, flags=re.IGNORECASE)
    words = stripped.lower().split()
    return bool(words) and words[0] in _Q_WORDS


# ============================================================
# GENERIC "MASTER" SECTION + TABLE CAPTURE (dynamic, self-adapting)
# ============================================================
# Related-jobs / author / ad / cross-link sections jo content nahi hain.
_SECTION_NOISE_RE = re.compile(
    r"(other\s+active|other\s+(latest\s+)?(govt\s+)?(jobs|recruitment)|"
    r"you\s+may\s+be\s+interested|you\s+might\s+be\s+interested|other\s+posts|"
    r"about\s+the\s+author|don'?t\s*miss|never\s+miss|also\s+read|"
    r"related\s+(posts|jobs|articles)|latest\s+notifications|follow\s+us|"
    r"^tags\b|comments?$)",
    re.IGNORECASE,
)


def extract_content_sections(content, clean=None, max_text=3000):
    """DYNAMIC MASTER CAPTURE — har h2 section ka heading + uski saari tables
    (structured list-of-dicts, multi-column matrix bhi preserve) + prose text
    ko capture karta hai.

    Fayda:
      - Har table apne SECTION HEADING ke saath alag rehti hai (kabhi mix nahi).
      - Multi-column matrix tables (Fee: Stage|General|Reserved|Ex-serv) poori
        preserve hoti hain, flatten nahi.
      - NAYA section/table jo site future me add kare, woh AUTOMATICALLY aa jayega
        — koi hardcoded field/keyword nahi, isliye baar-baar code fix nahi karna.

    Returns list of:
      { "heading": <section title>,
        "text":    <section prose>,
        "tables":  [ { "caption": <sub-heading/caption>, "rows": [ {..}, .. ] }, .. ] }
    """
    clean = clean or _default_clean
    sections = []
    for h2 in content.find_all("h2"):
        heading = clean(h2.get_text(" "))
        if not heading or _SECTION_NOISE_RE.search(heading):
            continue
        sibs = []
        for sib in h2.find_next_siblings():
            if sib.name == "h2":
                break
            sibs.append(sib)

        # --- tables (each isolated, with its own caption) ---
        tables_out, seen = [], set()
        for sib in sibs:
            nm = getattr(sib, "name", None)
            tbls = ([sib] if nm == "table"
                    else sib.find_all("table") if nm in ("div", "figure", "section")
                    else [])
            for tbl in tbls:
                if id(tbl) in seen:
                    continue
                seen.add(id(tbl))
                rows = parse_table_matrix(tbl, clean=clean)
                if not rows:
                    continue
                cap = _table_caption(tbl, clean)
                if cap == heading or (cap and _SECTION_NOISE_RE.search(cap)):
                    cap = ""
                tables_out.append({"caption": cap, "rows": rows})

        # --- prose (ad-filtered, table-cell text excluded) ---
        prose = []
        for sib in sibs:
            nm = getattr(sib, "name", None)
            if nm in ("p", "ul", "ol"):
                t = clean(sib.get_text(" "))
            elif nm == "div":
                if sib.find("table"):
                    t = clean(" ".join(s for s in sib.find_all(string=True)
                                       if not s.find_parent("table")))
                else:
                    t = clean(sib.get_text(" "))
            else:
                continue
            if t and not is_ad_text(t):
                prose.append(t)

        # Single-table section me caption ki zarurat nahi (heading hi title hai) —
        # sirf multi-table sections me caption rakho (tables distinguish karne ko).
        if len(tables_out) <= 1:
            for t in tables_out:
                t["caption"] = ""

        if tables_out or prose:
            sections.append({
                "heading": heading,
                "text":    " ".join(prose)[:max_text],
                "tables":  tables_out,
            })
    return sections
