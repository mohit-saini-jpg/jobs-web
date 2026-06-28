#!/usr/bin/env python3
"""
ai_html_enricher.py — TSJ AI HTML Enricher v1.0
=================================================
HTML files seedha read karo → facts extract karo → Groq API → HTML mein write karo
JSON mein kuch nahi likhna.

Usage:
  python3 ai_html_enricher.py                    # all pages
  python3 ai_html_enricher.py --dry-run          # count only
  python3 ai_html_enricher.py --slug <slug>      # single page test
  python3 ai_html_enricher.py --force            # re-enrich already done pages
"""

import os, sys, re, json, time, urllib.request, urllib.error
import html as _html
from pathlib import Path
from datetime import datetime
from hashlib import md5

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_KEY     = os.environ.get("GROQ_API_KEY", "").strip()
MODEL        = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
SAFE_RPM     = max(1, int(os.environ.get("GROQ_SAFE_RPM", "3")))
DELAY_SEC    = 60.0 / SAFE_RPM                    # 20s at 3 RPM
DAILY_LIMIT  = int(os.environ.get("DAILY_LIMIT", "800"))
RUN_LIMIT    = int(os.environ.get("RUN_LIMIT", "800"))
FORCE        = "--force" in sys.argv or os.environ.get("FORCE_REGEN","false").lower() == "true"
DRY_RUN      = "--dry-run" in sys.argv
JOBS_DIR     = Path(os.environ.get("JOBS_DIR", "jobs"))
PROGRESS_FILE = Path(".ai_progress_html.json")

SINGLE_SLUG  = None
for i, a in enumerate(sys.argv):
    if a == "--slug" and i+1 < len(sys.argv):
        SINGLE_SLUG = sys.argv[i+1]

# AI marker — HTML mein inject hone ke baad iska presence check karte hain
AI_MARKER = ""

# ── Helpers ───────────────────────────────────────────────────────────────────
def e(s): return _html.escape(str(s or ""), quote=True)
def ue(s): return _html.unescape(str(s or ""))
def striptags(s): return re.sub(r"<[^>]+>", "", str(s or "")).strip()

def sec_card(heading, icon, grad, body):
    return (
        f'<section class="sec-card">'
        f'<div class="sec-head" style="background:linear-gradient(135deg,#{grad})">'
        f'<i class="fa-solid {icon}"></i><h2>{e(heading)}</h2></div>'
        f'<div class="sec-body">{body}</div></section>\n'
    )

def render_faq(faq_list):
    if not isinstance(faq_list, list): return ""
    items = ""; seen = set(); idx = 0
    for f in faq_list:
        if not isinstance(f, dict): continue
        q = striptags(f.get("question","")); a = striptags(f.get("answer",""))
        if not q or not a: continue
        def _looksq(s):
            sl = s.strip().lower()
            return sl.endswith("?") or bool(re.match(
                r"^(what|when|how|who|where|which|is|are|can|will|does|do|why)\b",sl))
        if _looksq(a) and not _looksq(q): q, a = a, q
        q = re.sub(r"^\s*Q?\s*\d{1,3}\s*[\.\):\-]\s*","",q,flags=re.I).strip()
        key = re.sub(r"\s+"," ",q.lower()).strip()
        if not key or key in seen: continue
        seen.add(key); idx += 1
        op = " open" if idx==1 else ""
        items += (f'<div class="faq-item" id="faq-{idx}">'
                  f'<div class="faq-q{op}"><span class="faq-icon">Q{idx}</span>'
                  f'<span class="faq-q-text">{e(q)}</span>'
                  f'<i class="fa-solid fa-chevron-down faq-chev"></i></div>'
                  f'<div class="faq-a{op}"><span class="faq-a-icon faq-icon" style="background:#15803d">A</span>'
                  f'<div>{e(a)}</div></div></div>')
    return items

# ── Facts extractor from HTML ─────────────────────────────────────────────────
def extract_facts(html: str, slug: str) -> dict:
    """HTML se job facts nikalo — JSON-LD + kv-table + heading"""
    facts = {"slug": slug}

    # 1. Title from <title>
    m = re.search(r"<title>([^<]+)</title>", html)
    if m:
        facts["title"] = ue(m.group(1)).replace(" | Top Sarkari Jobs","").strip()

    # 2. JSON-LD JobPosting
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        try:
            jd = json.loads(block)
            if jd.get("@type") == "JobPosting":
                facts["organization"]    = striptags(jd.get("hiringOrganization",{}).get("name",""))
                facts["location"]        = striptags(jd.get("jobLocation",{}).get("address",{}).get("addressRegion","") or "India")
                facts["totalPosts"]      = str(jd.get("totalJobOpenings",""))
                facts["applicationMode"] = striptags(jd.get("employmentType",""))
                ld = jd.get("validThrough") or jd.get("applicationDeadline","")
                if ld: facts["lastDate"] = ld[:10]
                sal = jd.get("baseSalary",{})
                if isinstance(sal, dict):
                    v = sal.get("value",{})
                    if isinstance(v, dict):
                        mn = v.get("minValue",""); mx = v.get("maxValue","")
                        if mn or mx: facts["salary"] = f"{mn}-{mx}" if mx else str(mn)
                break
        except: pass

    # 3. kv-table rows (Organization Name, Total Vacancies, etc.)
    kv_rows = re.findall(r'<th>([^<]+)</th><td>([^<]+)</td>', html)
    for k, v in kv_rows:
        k2 = striptags(k).strip().lower()
        v2 = striptags(ue(v)).strip()
        if "organization" in k2 and not facts.get("organization"): facts["organization"] = v2
        elif "total" in k2 and "vacanc" in k2 and not facts.get("totalPosts"):  facts["totalPosts"] = v2
        elif "post name" in k2 and not facts.get("postName"):     facts["postName"] = v2
        elif "application mode" in k2:                             facts["applicationMode"] = v2
        elif "job location" in k2 and not facts.get("location"):  facts["location"] = v2
        elif "salary" in k2 and not facts.get("salary"):          facts["salary"] = v2

    # 4. Important dates
    dates = {}
    date_rows = re.findall(
        r'<i class="fa-regular fa-calendar"></i>\s*([^<]+)</th><td[^>]*>([^<]+)</td>',
        html)
    for k, v in date_rows:
        dates[striptags(k).strip()] = striptags(v).strip()
    if dates: facts["importantDates"] = dates

    # 5. Section headings (tells API what categories of info are present)
    headings = re.findall(r'<h2>([^<]+)</h2>', html)
    if headings:
        facts["sections"] = [ue(h) for h in headings if h not in ("Overview","Expert Analysis","Who Should Apply","Preparation Tips","Salary Insights","Job Profile","Selection Strategy","FAQs")]

    # 6. Meta description (existing, for context)
    meta_m = re.search(r'<meta name="description" content="([^"]+)"', html)
    if meta_m: facts["existingMeta"] = ue(meta_m.group(1))[:200]

    return {k: v for k, v in facts.items() if v}

# ── Groq API ──────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """\
You are a veteran Sarkari Naukri journalist writing for Indian government job aspirants.
Write in natural Hinglish (Hindi words in English script + English terms mixed naturally).

JOB FACTS:
{facts_json}

Generate EXACTLY this JSON (no extra text, no markdown):
{{
  "ai_title":              "<SEO title ≤65 chars, brand name first>",
  "ai_meta_description":   "<compelling meta ≤155 chars, include key facts>",
  "ai_h1":                 "<punchy H1, different from title, ≤80 chars>",
  "ai_overview":           "<2-3 sentences natural Hinglish overview, aspirant-friendly>",
  "ai_expert_analysis":    "<2-3 sentences expert take on this notification>",
  "ai_who_should_apply":   "<1-2 sentences on ideal candidate profile>",
  "ai_preparation_tips":   "<2-3 actionable prep tips>",
  "ai_salary_insights":    "<salary context, comparison, growth prospects>",
  "ai_job_profile_analysis":"<job role, day-to-day work, career growth>",
  "ai_selection_strategy": "<selection process strategy, what to focus on>",
  "ai_expanded_faqs":      [
    {{"question":"<Q?>","answer":"<A>"}},
    {{"question":"<Q?>","answer":"<A>"}},
    {{"question":"<Q?>","answer":"<A>"}}
  ]
}}"""

def call_groq(facts: dict) -> dict | None:
    if not GROQ_KEY:
        print("  ❌ GROQ_API_KEY missing")
        return None

    facts_json = json.dumps(facts, ensure_ascii=False, indent=2)
    prompt = PROMPT_TEMPLATE.format(facts_json=facts_json)

    body = {
        "model": MODEL,
        "max_tokens": 900,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}]
    }

    for attempt in range(4):
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GROQ_KEY}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = json.loads(resp.read().decode())
                content = raw["choices"][0]["message"]["content"].strip()
                content = re.sub(r"^```json\s*", "", content, flags=re.I)
                content = re.sub(r"```$", "", content).strip()
                return json.loads(content)

        except urllib.error.HTTPError as ex:
            body_err = ex.read().decode(errors="replace")
            if ex.code == 429:
                wait = 60 + attempt*30
                print(f"  ⏳ Rate limit 429 — waiting {wait}s...")
                time.sleep(wait)
            elif ex.code == 400:
                if "rate_limit" in body_err.lower() or "tokens" in body_err.lower():
                    wait = 60 + attempt*30
                    print(f"  ⏳ TPM overflow 400 — waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  ❌ Bad request: {body_err[:120]}")
                    return None
            elif ex.code in (401, 403):
                print(f"  ❌ Auth error {ex.code} — Groq response: {body_err[:300]}")
                # Key invalid hai — aage sab fail honge, abort karo
                print(f"  🛑 ABORTING — fix GROQ_API_KEY secret and retry")
                sys.exit(1)
            else:
                print(f"  ❌ HTTP {ex.code}: {body_err[:80]}")
                return None
        except Exception as ex:
            print(f"  ❌ Error attempt {attempt+1}: {ex}")
            time.sleep(10)

    return None

# ── HTML Patcher ──────────────────────────────────────────────────────────────
def patch_html(original: str, result: dict) -> str:
    html = original

    # Remove old AI block if present (full re-patch on --force)
    if AI_MARKER in html:
        html = re.sub(
            re.escape(AI_MARKER) + r".*?" + re.escape(AI_MARKER),
            "", html, flags=re.DOTALL)

    # 1. Build AI sections HTML
    ai_cards = [
        ("ai_overview",             "Overview",           "fa-circle-info",        "1d4ed8,#3b82f6"),
        ("ai_expert_analysis",      "Expert Analysis",    "fa-lightbulb",          "7c3aed,#a855f7"),
        ("ai_who_should_apply",     "Who Should Apply",   "fa-user-check",         "0