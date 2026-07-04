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
AI_MARKER = "<!-- tsj-ai-enriched -->"

# ── Helpers ───────────────────────────────────────────────────────────────────
def e(s): return _html.escape(str(s or ""), quote=True)
def ue(s): return _html.unescape(str(s or ""))
def striptags(s): return re.sub(r"<[^>]+>", "", str(s or "")).strip()

# Strip leaked "Don't Miss" sidebar widget text that the scraper concatenates
# onto short_information — same pattern as generate_all.py's sanitize_short_info.
_DONT_MISS_RE = re.compile(r"DON[''']?T\s+MISS.*", re.I | re.S)
def _sanitize(text): return _DONT_MISS_RE.sub("", str(text or "")).strip()

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

    # 6. Meta description (existing, for context) — sanitize DON'T MISS pollution
    meta_m = re.search(r'<meta name="description" content="([^"]+)"', html)
    if meta_m:
        _meta_raw = _sanitize(ue(meta_m.group(1)))
        if len(_meta_raw) >= 20:
            facts["existingMeta"] = _meta_raw[:200]

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

# Sentinel: a persistent rate/quota limit was hit — the caller should stop the
# run CLEANLY (and still print the final report) rather than kill the process.
RATE_LIMITED = object()


def _extract_json(content: str):
    """Parse the model's reply into a dict. With JSON mode this is a direct
    json.loads; the repair steps are a safety net for stray control chars /
    trailing commas that occasionally slip through with non-ASCII (Hindi) text."""
    content = (content or "").strip()
    content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.I)
    content = re.sub(r"\s*```$", "", content).strip()
    try:
        return json.loads(content)
    except Exception:
        pass
    i, j = content.find("{"), content.rfind("}")
    if i != -1 and j != -1 and j > i:
        frag = content[i:j + 1]
        no_trail = re.sub(r",\s*([}\]])", r"\1", frag)   # kill trailing commas
        no_ctrl  = re.sub(r"[\x00-\x1f]", " ", no_trail)  # literal control chars/newlines in strings
        for f in (frag, no_trail, no_ctrl):
            try:
                return json.loads(f)
            except Exception:
                continue
    return None


def _retry_after_secs(ex) -> float | None:
    try:
        ra = ex.headers.get("retry-after") or ex.headers.get("Retry-After")
        return float(ra) if ra else None
    except Exception:
        return None


def call_groq(facts: dict):
    """Returns a dict on success, None on a soft failure (skip this page), or the
    RATE_LIMITED sentinel when the daily quota is genuinely exhausted."""
    if not GROQ_KEY:
        print("  ❌ GROQ_API_KEY missing")
        return None

    prompt = PROMPT_TEMPLATE.format(facts_json=json.dumps(facts, ensure_ascii=False, indent=2))
    body = {
        "model": MODEL,
        "max_tokens": 800,
        "temperature": 0.2,                          # low temp → stable, valid JSON
        "response_format": {"type": "json_object"},  # JSON mode → no more malformed replies
        "messages": [{"role": "user", "content": prompt}],
    }

    rate_waits = 0
    for attempt in range(6):
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {GROQ_KEY}"},
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = json.loads(resp.read().decode())
            content = raw["choices"][0]["message"]["content"]
            parsed = _extract_json(content)
            if parsed is not None:
                return parsed
            # JSON mode should prevent this; if it still happens, retry cold once
            print(f"  ⚠️  JSON parse fail (attempt {attempt+1}) — retrying deterministically")
            body["temperature"] = 0.0
            time.sleep(3)
            continue

        except urllib.error.HTTPError as ex:
            try:
                body_err = ex.read().decode(errors="replace")
            except Exception:
                body_err = ""
            if ex.code == 429:
                ra = _retry_after_secs(ex)
                # Groq's TPM (tokens-per-minute) 429 resets in seconds — just wait
                # the header amount and retry. Only a large retry-after means the
                # DAILY quota is done → stop cleanly and resume next run.
                if ra is not None and ra > 150:
                    print(f"  🔴 Daily quota reached (retry-after ~{int(ra)}s) — resume next run")
                    return RATE_LIMITED
                rate_waits += 1
                if rate_waits > 10:
                    print("  🔴 Persistent rate limit — pausing run (report below)")
                    return RATE_LIMITED
                wait = ra if ra else min(8 * rate_waits, 45)
                print(f"  ⏳ Rate limit — waiting {wait:.0f}s then retrying (page NOT skipped)…")
                time.sleep(wait)
                continue
            if ex.code in (401, 403):
                print(f"  ❌ Auth error {ex.code}: {body_err[:220]}")
                print("  🛑 ABORTING — fix GROQ_API_KEY secret and retry")
                sys.exit(1)
            if ex.code == 400 and ("rate" in body_err.lower() or "token" in body_err.lower()):
                print("  ⏳ Token overflow — waiting 20s…")
                time.sleep(20)
                continue
            print(f"  ❌ HTTP {ex.code}: {body_err[:120]}")
            return None
        except Exception as ex:
            print(f"  ❌ Error attempt {attempt+1}: {ex}")
            time.sleep(6)

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
        ("ai_who_should_apply",     "Who Should Apply",   "fa-user-check",         "0f766e,#0891b2"),
        ("ai_preparation_tips",     "Preparation Tips",   "fa-list-check",         "047857,#10b981"),
        ("ai_salary_insights",      "Salary Insights",    "fa-indian-rupee-sign",  "b45309,#f59e0b"),
        ("ai_job_profile_analysis", "Job Profile",        "fa-briefcase",          "475569,#334155"),
        ("ai_selection_strategy",   "Selection Strategy", "fa-bullseye",           "be123c,#f43f5e"),
    ]
    ai_html = ""
    for key, heading, icon, color in ai_cards:
        val = striptags(result.get(key) or "").strip()
        if val and len(val) > 20:
            body = f'<div class="edu-sec" style="line-height:1.7">{e(val)}</div>'
            ai_html += sec_card(heading, icon, color, body)

    # FAQ
    faqs = result.get("ai_expanded_faqs") or []
    faq_html = render_faq(faqs) if faqs else ""
    if faq_html:
        ai_html += sec_card("FAQs", "fa-circle-question", "0f172a,#1e293b",
                            f'<div class="faq-wrap">{faq_html}</div>')

    if ai_html:
        # Wrap in markers so we can find/replace on next run
        ai_block = f"\n{AI_MARKER}\n{ai_html}{AI_MARKER}\n"
        # Insert BEFORE first sec-card
        pos = html.find('<section class="sec-card">')
        if pos != -1:
            html = html[:pos] + ai_block + html[pos:]
        else:
            for tag in ["</main>", "</article>", "</body>"]:
                pos = html.rfind(tag)
                if pos != -1:
                    html = html[:pos] + ai_block + html[pos:]
                    break

    # 2. Title tag
    ai_title = striptags(result.get("ai_title") or "").strip()
    if ai_title:
        site = " | Top Sarkari Jobs"
        title_with_brand = (ai_title[:65-len(site)] + site) if len(ai_title) > 60 else (ai_title + site)
        html = re.sub(
            r'(<title>)(.*?)(</title>)',
            lambda m: m.group(1) + e(title_with_brand) + m.group(3),
            html, count=1, flags=re.DOTALL)

    # 3. Meta description
    ai_meta = striptags(result.get("ai_meta_description") or "").strip()
    if ai_meta:
        html = re.sub(
            r'(<meta\s+name=["\']description["\']\s+content=["\'])([^"\']*?)(["\'])',
            lambda m: m.group(1) + e(ai_meta[:155]) + m.group(3),
            html, count=1, flags=re.IGNORECASE)

    # 4. H1
    ai_h1 = striptags(result.get("ai_h1") or "").strip()
    if ai_h1:
        html = re.sub(
            r'(<h1[^>]*class="[^"]*post-title[^"]*"[^>]*>)(.*?)(</h1>)',
            lambda m: m.group(1) + e(ai_h1) + m.group(3),
            html, count=1, flags=re.DOTALL|re.IGNORECASE)

    return html

# ── Progress tracking ─────────────────────────────────────────────────────────
def load_progress():
    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except: return {"done_slugs": [], "calls_today": 0, "date": ""}

def save_progress(p):
    tmp = PROGRESS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
    tmp.replace(PROGRESS_FILE)

def site_progress(base: Path):
    """Scan the whole jobs tree: how many pages already carry AI content vs not.
    Answers 'kitne HTML me data add hua, kitne bache' site-wide (persists across
    days via the AI_MARKER baked into each page — not the daily progress file)."""
    total = enriched = 0
    for f in base.rglob("index.html"):
        total += 1
        try:
            if AI_MARKER in f.read_text(encoding="utf-8", errors="ignore"):
                enriched += 1
        except Exception:
            pass
    return enriched, total

def write_summary(lines):
    """Append a Markdown block to the GitHub Actions run summary (if running in CI)."""
    gs = os.environ.get("GITHUB_STEP_SUMMARY")
    if not gs:
        return
    try:
        with open(gs, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass

# ── Git commit ────────────────────────────────────────────────────────────────
def git_commit(count, calls):
    import subprocess
    try:
        subprocess.run(["git","config","user.name","github-actions[bot]"],capture_output=True)
        subprocess.run(["git","config","user.email","github-actions[bot]@users.noreply.github.com"],capture_output=True)
        subprocess.run(["git","add","jobs/"],capture_output=True)
        r = subprocess.run(["git","diff","--staged","--quiet"],capture_output=True)
        if r.returncode != 0:
            msg = f"🤖 AI HTML: {count} pages enriched ({calls} API calls) | {datetime.now().strftime('%Y-%m-%d %H:%M')} [skip ci]"
            subprocess.run(["git","commit","-m",msg],capture_output=True)
            subprocess.run(["git","push","origin","main"],capture_output=True)
            print(f"  💾 Git commit: {count} pages pushed")
    except Exception as ex:
        print(f"  ⚠️  Git commit skip: {ex}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🤖 TSJ AI HTML Enricher v1.0")
    print("=" * 60)
    print(f"   Model    : {MODEL}")
    print(f"   Rate     : {SAFE_RPM} RPM = {DELAY_SEC:.0f}s delay")
    print(f"   Run limit: {RUN_LIMIT} pages")
    print(f"   Jobs dir : {JOBS_DIR}")
    print(f"   Mode     : {'DRY RUN' if DRY_RUN else 'FORCE' if FORCE else 'NORMAL'}")
    print()

    if not JOBS_DIR.exists():
        print(f"❌ {JOBS_DIR} not found — run from repo root")
        sys.exit(1)

    # Load progress
    progress = load_progress()
    today = datetime.now().strftime("%Y-%m-%d")
    if progress.get("date") != today:
        progress = {"done_slugs": [], "calls_today": 0, "date": today}
    done_slugs = set(progress["done_slugs"])
    calls_today = progress["calls_today"]

    enr0, tot0 = site_progress(JOBS_DIR)
    print(f"📊 Site coverage: {enr0}/{tot0} job pages enriched  |  {tot0 - enr0} remaining")
    print(f"📊 Today: {calls_today}/{DAILY_LIMIT} API calls used")
    if calls_today >= DAILY_LIMIT:
        print("   ℹ️  Aaj ka daily quota already use ho chuka — kal fresh run pe agle pages honge (ye normal hai).")
    print()

    # Collect HTML files to process — NEWEST first so fresh jobs get AI content
    # promptly. Already-enriched pages are skipped (AI_MARKER), so the backlog of
    # older un-enriched pages still drains over subsequent days.
    if SINGLE_SLUG:
        html_files = [JOBS_DIR / SINGLE_SLUG / "index.html"]
    else:
        html_files = sorted(JOBS_DIR.rglob("index.html"),
                            key=lambda p: p.stat().st_mtime, reverse=True)

    processed = 0
    skipped_done = 0
    skipped_ai = 0
    errors = 0
    failed_slugs = []          # pages the API couldn't enrich → retried next run
    rate_stopped = False       # True if we stopped early due to daily quota

    for html_path in html_files:
        if processed >= RUN_LIMIT:
            print(f"\n🔴 RUN_LIMIT ({RUN_LIMIT}) reached")
            break
        if calls_today >= DAILY_LIMIT:
            print(f"\n🔴 DAILY_LIMIT ({DAILY_LIMIT}) reached")
            break

        if not html_path.exists():
            print(f"  ❌ Not found: {html_path}")
            continue

        slug = html_path.parent.name

        # Skip if already done today
        if not FORCE and slug in done_slugs:
            skipped_done += 1
            continue

        # Read HTML
        try:
            original = html_path.read_text(encoding="utf-8")
        except Exception as ex:
            print(f"  ❌ Read error [{slug}]: {ex}")
            errors += 1
            continue

        # ── Microdata inject (no API needed) ─────────────────────
        md_html, md_changed = inject_missing_microdata(original)
        if md_changed and not DRY_RUN:
            tmp = html_path.with_suffix(".tmp")
            tmp.write_text(md_html, encoding="utf-8")
            tmp.replace(html_path)
            original = md_html   # updated original for AI patch below
            print(f"   📋 Microdata injected (JobPosting itemprop)")

        # Skip if already has AI content (and not forcing)
        if not FORCE and AI_MARKER in original:
            skipped_ai += 1
            done_slugs.add(slug)
            continue

        # Extract facts from HTML
        facts = extract_facts(original, slug)
        if not facts.get("title"):
            skipped_done += 1
            continue

        print(f"\n⚡ [{processed+1}/{RUN_LIMIT}] [{calls_today+1}/{DAILY_LIMIT}]")
        print(f"   {facts.get('title','')[:65]}")
        print(f"   Org: {facts.get('organization','?')[:50]}")

        if DRY_RUN:
            print(f"   🔵 DRY RUN — would call API")
            processed += 1
            continue

        # Call Groq
        result = call_groq(facts)
        if result is RATE_LIMITED:
            # Daily quota done — stop THIS run cleanly. Progress is saved, the
            # final report still prints, and remaining pages resume next run.
            print("   ⏸️  Daily quota reached — stopping this run cleanly (report below)")
            rate_stopped = True
            break
        if not result:
            errors += 1
            failed_slugs.append(slug)      # not marked done → retried next run
            print(f"   ⚠️  API returned nothing — will retry next run")
            continue

        # Patch HTML
        new_html = patch_html(original, result)

        # Atomic write
        tmp = html_path.with_suffix(".tmp")
        tmp.write_text(new_html, encoding="utf-8")
        tmp.replace(html_path)

        print(f"   ✅ Done — HTML patched")

        processed += 1
        calls_today += 1
        done_slugs.add(slug)

        # Save progress
        progress["done_slugs"] = list(done_slugs)
        progress["calls_today"] = calls_today
        save_progress(progress)

        # Har 10 pages ke baad commit — cancel hone par max 10 pages ka loss
        if processed % 10 == 0:
            git_commit(processed, calls_today)

        time.sleep(DELAY_SEC)

    # Final git commit
    if processed > 0 and not DRY_RUN:
        git_commit(processed, calls_today)

    enr1, tot1 = site_progress(JOBS_DIR)
    remaining = tot1 - enr1
    days_left = (remaining + DAILY_LIMIT - 1) // max(1, DAILY_LIMIT)
    pct = (enr1 * 100.0 / tot1) if tot1 else 0.0
    stop_reason = ("Daily quota reached" if rate_stopped else
                   "RUN_LIMIT reached" if processed >= RUN_LIMIT else
                   "Daily API budget used" if calls_today >= DAILY_LIMIT else
                   "All targeted pages processed")

    print()
    print("=" * 60)
    print("  📋 AI ENRICHMENT — FINAL REPORT")
    print("=" * 60)
    print(f"  ✅ Enriched this run : {processed}")
    print(f"  ⏭️  Already had AI    : {skipped_ai}")
    print(f"  ⏭️  Skipped (no data) : {skipped_done}")
    print(f"  ❌ Failed (retry)    : {errors}" + (f"  e.g. {', '.join(failed_slugs[:3])}" if failed_slugs else ""))
    print(f"  🔢 API calls today   : {calls_today}/{DAILY_LIMIT}")
    print(f"  ⏹️  Stopped because   : {stop_reason}")
    print("  " + "-" * 56)
    print(f"  📊 SITE COVERAGE     : {enr1}/{tot1} pages enriched ({pct:.1f}%)")
    print(f"  📄 REMAINING         : {remaining} pages  (~{days_left} more day(s) @ {DAILY_LIMIT}/day)")
    print("=" * 60)

    # Save the failed list so we can see what needs a retry (naturally re-tried
    # next run since failures are never marked done).
    try:
        progress["last_failed"] = failed_slugs[:50]
        progress["last_run"] = datetime.now().isoformat(timespec="seconds")
        save_progress(progress)
    except Exception:
        pass

    bar_done = int(pct / 5)
    bar = "█" * bar_done + "░" * (20 - bar_done)
    write_summary([
        "### 🤖 AI Content Enrichment — Nightly Report",
        "",
        f"**Coverage:** `{bar}` **{pct:.1f}%**  ({enr1}/{tot1} pages)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| ✅ Enriched this run | **{processed}** |",
        f"| 📄 Remaining | **{remaining}** |",
        f"| ❌ Failed (auto-retry next run) | {errors} |",
        f"| 🔢 API calls today | {calls_today}/{DAILY_LIMIT} |",
        f"| ⏱️ Est. days to 100% | ~{days_left} (at {DAILY_LIMIT}/day) |",
        f"| ⏹️ Stopped because | {stop_reason} |",
    ])

# ══════════════════════════════════════════════════════════════════
# MICRODATA INJECTOR — Google crawl fields (no API needed)
# JSON-LD se values extract → hidden microdata <div> inject
# ══════════════════════════════════════════════════════════════════

MICRODATA_MARKER = "<!-- tsj-microdata -->"

def extract_jsonld(html: str, type_name: str) -> dict:
    """HTML se specific @type ka JSON-LD block extract karo."""
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        try:
            jd = json.loads(block)
            if jd.get("@type") == type_name:
                return jd
        except:
            pass
    return {}

def build_microdata_block(jd: dict) -> str:
    """
    JobPosting JSON-LD → Google-crawlable microdata HTML block.
    Hidden div — visually invisible, Google reads it.
    """
    if not jd:
        return ""

    # ── Extract values from JSON-LD ───────────────────────────────
    title        = striptags(jd.get("title", ""))
    description  = striptags(jd.get("description", ""))
    date_posted  = jd.get("datePosted", "")
    valid_through = (jd.get("validThrough") or jd.get("applicationDeadline") or "")
    # Normalize date: "2026-07-30T00:00:00" → "2026-07-30"
    if valid_through and "T" in valid_through:
        valid_through = valid_through.split("T")[0]
    employment_type = jd.get("employmentType", "FULL_TIME")
    direct_apply    = str(jd.get("directApply", "True")).lower()
    direct_apply    = "True" if direct_apply in ("true", "1") else "False"

    # hiringOrganization
    hiring_org  = jd.get("hiringOrganization", {})
    org_name    = striptags(hiring_org.get("name", "") if isinstance(hiring_org, dict) else "")
    org_url     = hiring_org.get("sameAs", "") if isinstance(hiring_org, dict) else ""

    # jobLocation
    job_loc     = jd.get("jobLocation", {})
    address     = job_loc.get("address", {}) if isinstance(job_loc, dict) else {}
    city        = striptags(address.get("addressLocality", "India") if isinstance(address, dict) else "India")
    region      = striptags(address.get("addressRegion", "") if isinstance(address, dict) else "")
    country     = address.get("addressCountry", "IN") if isinstance(address, dict) else "IN"
    postal      = address.get("postalCode", "") if isinstance(address, dict) else ""

    # baseSalary
    base_sal    = jd.get("baseSalary", {})
    sal_val     = base_sal.get("value", {}) if isinstance(base_sal, dict) else {}
    min_sal     = str(sal_val.get("minValue", "")) if isinstance(sal_val, dict) else ""
    max_sal     = str(sal_val.get("maxValue", "")) if isinstance(sal_val, dict) else ""
    currency    = base_sal.get("currency", "INR") if isinstance(base_sal, dict) else "INR"
    unit_text   = sal_val.get("unitText", "MONTH") if isinstance(sal_val, dict) else "MONTH"

    # ── Build microdata HTML ──────────────────────────────────────
    html_out = f'\n{MICRODATA_MARKER}\n'
    html_out += '<div itemscope itemtype="https://schema.org/JobPosting" style="display:none" aria-hidden="true">\n'

    # Required fields
    if title:
        html_out += f'  <meta itemprop="title" content="{e(title)}">\n'
    if description:
        # Keep description under 5000 chars
        desc_short = description[:5000]
        html_out += f'  <meta itemprop="description" content="{e(desc_short)}">\n'
    if date_posted:
        html_out += f'  <meta itemprop="datePosted" content="{e(date_posted)}">\n'
    if valid_through:
        html_out += f'  <meta itemprop="validThrough" content="{e(valid_through)}">\n'
    if employment_type:
        html_out += f'  <meta itemprop="employmentType" content="{e(employment_type)}">\n'
    html_out += f'  <meta itemprop="directApply" content="{direct_apply}">\n'

    # hiringOrganization
    if org_name:
        html_out += '  <div itemprop="hiringOrganization" itemscope itemtype="https://schema.org/Organization">\n'
        html_out += f'    <meta itemprop="name" content="{e(org_name)}">\n'
        if org_url:
            html_out += f'    <meta itemprop="url" content="{e(org_url)}">\n'
        html_out += '  </div>\n'

    # jobLocation
    html_out += '  <div itemprop="jobLocation" itemscope itemtype="https://schema.org/Place">\n'
    html_out += '    <div itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">\n'
    if city:
        html_out += f'      <meta itemprop="addressLocality" content="{e(city)}">\n'
    if region:
        html_out += f'      <meta itemprop="addressRegion" content="{e(region)}">\n'
    html_out += f'      <meta itemprop="addressCountry" content="{e(country)}">\n'
    if postal:
        html_out += f'      <meta itemprop="postalCode" content="{e(postal)}">\n'
    html_out += '    </div>\n  </div>\n'

    # baseSalary
    if min_sal or max_sal:
        html_out += '  <div itemprop="baseSalary" itemscope itemtype="https://schema.org/MonetaryAmount">\n'
        html_out += f'    <meta itemprop="currency" content="{e(currency)}">\n'
        html_out += '    <div itemprop="value" itemscope itemtype="https://schema.org/QuantitativeValue">\n'
        if min_sal:
            html_out += f'      <meta itemprop="minValue" content="{e(min_sal)}">\n'
        if max_sal:
            html_out += f'      <meta itemprop="maxValue" content="{e(max_sal)}">\n'
        html_out += f'      <meta itemprop="unitText" content="{e(unit_text)}">\n'
        html_out += '    </div>\n  </div>\n'

    # applicantLocationRequirements
    html_out += '  <div itemprop="applicantLocationRequirements" itemscope itemtype="https://schema.org/Country">\n'
    html_out += '    <meta itemprop="name" content="India">\n'
    html_out += '  </div>\n'

    html_out += f'</div>\n{MICRODATA_MARKER}\n'
    return html_out


def inject_missing_microdata(html: str) -> tuple[str, bool]:
    """
    Agar page mein JobPosting JSON-LD hai aur microdata nahi →
    microdata block inject karo </body> se pehle.
    Returns (new_html, was_changed)
    """
    # Already injected?
    if MICRODATA_MARKER in html:
        return html, False

    # Page mein JobPosting JSON-LD hai?
    jd = extract_jsonld(html, "JobPosting")
    if not jd:
        return html, False

    # Build microdata block from JSON-LD values
    microdata = build_microdata_block(jd)
    if not microdata:
        return html, False

    # Inject before </body>
    pos = html.rfind("</body>")
    if pos == -1:
        return html, False

    new_html = html[:pos] + microdata + html[pos:]
    return new_html, True

if __name__ == "__main__":
    main()
