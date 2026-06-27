#!/usr/bin/env python3
"""
ai_content_layer.py — TSJ AI Enrichment Engine v3.0
=====================================================
DESIGN PHILOSOPHY:
  - Sirf NAYE / UNPROCESSED jobs pe Groq API call karo
  - content_hash se detect karo: "ye job already done hai"
  - Raat ko cron se chalao — jitna Groq free allow kare utna karo
  - Kal wahi se resume karo jahan kal ruka tha
  - JSON push pe ye script NAHI chalti — sirf HTML build chalta hai
  - HTML generate_all.py automatically AI data use karta hai

GROQ FREE LIMITS (as of 2026):
  llama-3.1-8b-instant   : 30 RPM, 14400 RPD, 6000 TPM
  llama-3.3-70b-versatile: 30 RPM,  1000 RPD, 6000 TPM  ← preferred quality
  gemma2-9b-it           : 30 RPM, 14400 RPD, 15000 TPM

RATE LIMIT STRATEGY:
  - 5 RPM (safe) = 12s delay between calls
  - 1000 RPD safe limit = stop at DAILY_LIMIT jobs per day
  - Job ek baar process → content_hash set → KABHI dobara process nahi
"""
import os, re, sys, json, time, hashlib
import urllib.request, urllib.error
from datetime import datetime, timedelta
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG — GitHub Actions Secrets / env vars se aata hai
# ─────────────────────────────────────────────────────────────────────────────
DATA_FILE    = os.environ.get("AI_DATA_FILE", "Complete_Jobs_Full_Data.json")
MODEL        = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_KEY     = os.environ.get("GROQ_API_KEY", "").strip()

# Raat ko safe rate: 5 calls/minute = 12s gap. Free tier handle hoga.
SAFE_RPM     = max(1, int(os.environ.get("GROQ_SAFE_RPM", "5")))
DELAY_SEC    = 60.0 / SAFE_RPM          # = 12.0 seconds

# Per-day limit — Groq RPD limit ke andar rahna
# llama-3.3-70b: 1000 RPD, to 900 safe rakh
DAILY_LIMIT  = int(os.environ.get("DAILY_LIMIT", "900"))

# Ek GitHub Actions run me max kitna karo (timeout 40 min = ~180 calls safe)
RUN_LIMIT    = int(os.environ.get("RUN_LIMIT", "150"))

# Force re-generate — sirf agar explicitly set karo (bulk refresh ke liye)
FORCE_REGEN  = os.environ.get("FORCE_REGEN", "false").lower() == "true"

# Progress file — track karo aaj kitna hua, kahan ruke the
PROGRESS_FILE = ".ai_progress.json"

# ─────────────────────────────────────────────────────────────────────────────
# PROGRESS TRACKER — resume support
# ─────────────────────────────────────────────────────────────────────────────
def load_progress():
    """Aaj ka progress load karo."""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        p = json.load(open(PROGRESS_FILE, encoding="utf-8"))
        if p.get("date") == today:
            return p
    except Exception:
        pass
    return {"date": today, "calls_today": 0, "processed_slugs": []}

def save_progress(progress):
    tmp = PROGRESS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False)
    os.replace(tmp, PROGRESS_FILE)

# ─────────────────────────────────────────────────────────────────────────────
# STATE → LOCATION MAP
# ─────────────────────────────────────────────────────────────────────────────
STATE_MAP = {
    "DELHI": ("Delhi", "110001"), "UTTAR PRADESH": ("Uttar Pradesh", "226001"),
    "RAJASTHAN": ("Rajasthan", "302001"), "HARYANA": ("Haryana", "160017"),
    "BIHAR": ("Bihar", "800001"), "MADHYA PRADESH": ("Madhya Pradesh", "462001"),
    "PUNJAB": ("Punjab", "160001"), "JHARKHAND": ("Jharkhand", "834001"),
    "GUJARAT": ("Gujarat", "380001"), "MAHARASHTRA": ("Maharashtra", "400001"),
    "KARNATAKA": ("Karnataka", "560001"), "TAMIL NADU": ("Tamil Nadu", "600001"),
    "WEST BENGAL": ("West Bengal", "700001"), "ODISHA": ("Odisha", "751001"),
    "KERALA": ("Kerala", "695001"), "ANDHRA PRADESH": ("Andhra Pradesh", "520001"),
    "TELANGANA": ("Telangana", "500001"), "ASSAM": ("Assam", "781001"),
    "CHHATTISGARH": ("Chhattisgarh", "492001"), "UTTARAKHAND": ("Uttarakhand", "248001"),
    "HIMACHAL PRADESH": ("Himachal Pradesh", "171001"),
    "JHARKHAND": ("Jharkhand", "834001"), "MANIPUR": ("Manipur", "795001"),
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _s(v, maxlen=300):
    """Safe string from any value."""
    if v is None: return ""
    if isinstance(v, bool): return str(v)
    if isinstance(v, (int, float)): return str(v)
    if isinstance(v, list): return "; ".join(_s(x, 100) for x in v[:5] if x)
    if isinstance(v, dict):
        parts = []
        for k2, v2 in list(v.items())[:6]:
            sv = _s(v2, 80)
            if sv: parts.append(f"{k2}: {sv}")
        return " | ".join(parts)
    return str(v).strip()[:maxlen]

def get_title(job):
    """Extract title from any job format."""
    bd = job.get("basic_details") or {}
    return (
        _s(bd.get("job_title")) or _s(job.get("title")) or
        _s(job.get("name")) or ""
    ).strip()

def get_slug(job):
    """Get slug or derive from title."""
    s = job.get("slug") or job.get("_canonical_slug") or ""
    if s: return str(s).strip()[:80]
    t = get_title(job)
    if not t: return ""
    t = t.lower()
    t = re.sub(r'[^a-z0-9\s-]', '', t)
    t = re.sub(r'[\s_-]+', '-', t).strip('-')
    return t[:80]

def compute_hash(job):
    """
    Hash of fields that define "content version".
    Same job + same data → same hash → skip.
    Job ki date/vacancy change → new hash → re-process.
    """
    bd = job.get("basic_details") or {}
    dates = job.get("important_dates") or job.get("importantDates") or {}
    vac = job.get("vacancy_details") or job.get("vacancyDetails") or []
    keyed = {
        "title": get_title(job),
        "total": _s(bd.get("total_vacancies") or job.get("total_post") or job.get("totalPost")),
        "dates": {k: _s(v) for k, v in (list(dates.items())[:5] if isinstance(dates, dict) else [])},
        "vac_count": len(vac) if isinstance(vac, list) else 0,
    }
    return hashlib.md5(json.dumps(keyed, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def is_already_done(job, new_hash):
    """
    True agar ye job pehle se AI process ho chuka hai.
    Check: content_hash match AND ai_overview exist AND length > 100.
    """
    if FORCE_REGEN:
        return False
    existing_hash = job.get("content_hash", "")
    existing_overview = job.get("ai_overview", "")
    return (existing_hash == new_hash and
            isinstance(existing_overview, str) and
            len(existing_overview.strip()) > 100)

# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZE FACTS for prompt
# ─────────────────────────────────────────────────────────────────────────────
def normalize_facts(job):
    """Extract clean facts dict from job — handles both FJA and sarkari format."""
    bd = job.get("basic_details") or {}

    title = get_title(job)
    org = (_s(bd.get("organization_name")) or _s(job.get("organization")) or
           _s(job.get("board")) or "Government of India")
    posts = (_s(bd.get("total_vacancies")) or _s(job.get("total_post")) or
             _s(job.get("totalPost")) or _s(job.get("total_vacancy")) or "")
    location = (_s(bd.get("job_location")) or _s(job.get("job_location")) or
                _s(job.get("state")) or "India")
    mode = _s(bd.get("application_mode") or job.get("apply_mode") or "Online")

    # Dates
    dates_raw = (job.get("important_dates") or job.get("importantDates") or
                 (job.get("detail") or {}).get("important_dates") or {})
    dates = {}
    if isinstance(dates_raw, dict):
        for k, v in dates_raw.items():
            sv = _s(v, 60)
            if sv:
                lbl = re.sub(r'([a-z])([A-Z])', r'\1 \2', str(k)).replace('_', ' ').title()
                dates[lbl] = sv

    # Fee
    fee_raw = (job.get("application_fee") or job.get("applicationFee") or
               job.get("application_fees") or {})
    fee = {}
    if isinstance(fee_raw, dict):
        for k, v in fee_raw.items():
            sv = _s(v, 50)
            if sv: fee[k] = sv
    else:
        fee = {"details": _s(fee_raw, 100)}

    # Age
    age_raw = job.get("age_limit") or job.get("ageLimit") or {}
    age = {}
    if isinstance(age_raw, dict):
        for k, v in age_raw.items():
            sv = _s(v, 80)
            if sv: age[k] = sv
    else:
        age = {"details": _s(age_raw, 100)}

    # Vacancy details (first 8 only)
    vac = job.get("vacancy_details") or job.get("vacancyDetails") or []
    vac_summary = []
    if isinstance(vac, list):
        for row in vac[:8]:
            if isinstance(row, dict):
                post = _s(row.get("post_name") or row.get("postName") or "")
                total = _s(row.get("total") or row.get("total_post") or "")
                qual = _s(row.get("qualification") or row.get("eligibility") or "")
                if post or total:
                    vac_summary.append({"post": post, "total": total, "eligibility": qual[:100]})

    # Selection process
    sel = job.get("selection_process") or job.get("selectionProcess") or []
    if isinstance(sel, str): sel = [sel]
    sel_list = [_s(x, 80) for x in sel[:6] if _s(x)]

    # Salary
    sal_raw = (job.get("salary_details") or {})
    sal = _s(sal_raw.get("pay_scale") if isinstance(sal_raw, dict) else sal_raw, 100)
    if not sal:
        sal = _s(job.get("salary_pay_scale") or "", 100)

    # Links
    links = job.get("important_links") or job.get("importantLinks") or {}
    link_keys = {}
    if isinstance(links, dict):
        for k in ["apply_online", "official_website", "notification_pdf", "result_link", "admit_card"]:
            v = _s(links.get(k), 120)
            if v: link_keys[k] = v

    return {
        "title": title,
        "organization": org,
        "totalPosts": posts,
        "location": location,
        "applicationMode": mode,
        "importantDates": dates,
        "applicationFee": fee,
        "ageLimit": age,
        "vacancyDetails": vac_summary,
        "selectionProcess": sel_list,
        "salaryPayScale": sal,
        "importantLinks": link_keys,
        "category": _s(job.get("category") or "", 40),
    }

# ─────────────────────────────────────────────────────────────────────────────
# GROQ API CALL
# ─────────────────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """\
You are a veteran Sarkari Naukri journalist with 12+ years writing for Indian aspirants.
Write in natural Hinglish (Hindi words in English script mixed with English terms).

HARD RULES — Breaking any = fail:
1. NEVER use: "In conclusion", "Furthermore", "Moreover", "Additionally",
   "It is important to note", "Notably", "Overall", "In summary", "Lastly",
   "Needless to say", "It goes without saying", "Crucial"
2. NEVER repeat the same fact across different sections
3. NEVER write generic advice — everything must be specific to THIS job
4. Short paragraphs only (2-3 sentences max per paragraph)
5. Sound like a real coaching teacher talking to aspirants — not a bot

STYLE EXAMPLES (copy this tone):
- "Dosto, agar aap {{org}} me government job dhundh rahe hain toh yeh notification zaroor padhein."
- "Seedha baat karte hain — competition kaafi tough hoga kyunki..."
- "Form bharte waqt ek galti mat karna: ..."
- "Salary ki baat karein toh in-hand roughly..."

JOB DATA:
{facts_json}

Return ONLY valid JSON (no markdown, no extra text):
{{
  "ai_h1": "Catchy Hinglish headline under 90 chars with org + posts + year",
  "ai_title": "SEO title under 65 chars",
  "ai_meta_description": "Under 155 chars. Hook + vacancy count + last date.",
  "ai_overview": "2 short paragraphs. Who is hiring, how many posts, excitement factor. Natural Hinglish.",
  "ai_expert_analysis": "Competition level, difficulty, which posts have best chances. 2 paragraphs. Be specific.",
  "ai_who_should_apply": "Exact eligibility. Age range, education, states eligible. Who should NOT apply. 2 paragraphs.",
  "ai_preparation_tips": "3-4 practical tips specific to THIS exam/recruitment type. Physical test tips if applicable.",
  "ai_salary_insights": "In-hand estimate with DA/HRA. Allowances. Promotion path. Use actual numbers where known.",
  "ai_job_profile_analysis": "Day-to-day work. Field vs desk. Department culture. Real picture for aspirants.",
  "ai_selection_strategy": "Stage-wise strategy for this specific selection process. Which sections to focus on.",
  "ai_how_to_apply_rewrite": "Step-by-step 5-6 numbered steps. Common mistakes to avoid. Documents checklist.",
  "ai_expanded_faqs": [
    {{"question": "Real question an aspirant would Google about this job", "answer": "Specific 2-3 sentence answer"}}
  ],
  "ai_extracted_structured_data": {{
    "last_date": "YYYY-MM-DD",
    "job_location": "State Name",
    "postal_code": "6-digit pincode",
    "salary_range": "21700 - 69100"
  }}
}}
Generate 6-8 FAQs. Each FAQ must be specific to THIS job — no generic answers.\
"""

def call_groq(facts):
    """Call Groq API. Returns dict or None."""
    if not GROQ_KEY:
        return None

    facts_json = json.dumps(facts, ensure_ascii=False, indent=2)
    prompt = PROMPT_TEMPLATE.format(facts_json=facts_json)

    # Truncate if too long (Groq TPM limit)
    if len(prompt) > 15000:
        # Shorten vacancy details in facts
        facts_short = dict(facts)
        facts_short["vacancyDetails"] = facts["vacancyDetails"][:3]
        facts_json = json.dumps(facts_short, ensure_ascii=False, indent=2)
        prompt = PROMPT_TEMPLATE.format(facts_json=facts_json)

    url = "https://api.groq.com/openai/v1/chat/completions"
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.72,
        "max_tokens": 2800,
    }

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode())
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {GROQ_KEY}")
            req.add_header("User-Agent", "TSJ-AI/3.0")

            with urllib.request.urlopen(req, timeout=50) as resp:
                raw = json.loads(resp.read().decode())

            content = raw["choices"][0]["message"]["content"].strip()
            content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
            return json.loads(content)

        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="ignore")[:200]
            if e.code == 429:
                # Rate limited — extract retry-after if present
                wait = 60
                if "retry-after" in body_err.lower():
                    m = re.search(r'"retry_after":\s*(\d+)', body_err)
                    if m: wait = int(m.group(1)) + 5
                print(f"    ⏳ Rate limit — waiting {wait}s...")
                time.sleep(wait)
                continue
            elif e.code in (400, 401, 403):
                print(f"    ❌ Auth error {e.code} — check GROQ_API_KEY secret")
                return None
            else:
                print(f"    ⚠️  HTTP {e.code}: {body_err[:80]}")
                time.sleep(8 * (attempt + 1))

        except json.JSONDecodeError as je:
            print(f"    ⚠️  JSON parse fail attempt {attempt+1}: {je}")
            time.sleep(5)
        except Exception as ex:
            print(f"    ⚠️  Error attempt {attempt+1}: {ex}")
            time.sleep(8)

    return None

# ─────────────────────────────────────────────────────────────────────────────
# APPLY RESULT TO JOB
# ─────────────────────────────────────────────────────────────────────────────
TEXT_KEYS = [
    "ai_h1", "ai_title", "ai_meta_description", "ai_overview",
    "ai_expert_analysis", "ai_who_should_apply", "ai_preparation_tips",
    "ai_salary_insights", "ai_job_profile_analysis", "ai_selection_strategy",
    "ai_how_to_apply_rewrite",
]

def apply_result(job, result):
    if not isinstance(result, dict): return False
    applied = False
    for k in TEXT_KEYS:
        v = result.get(k)
        if isinstance(v, str) and len(v.strip()) > 20:
            job[k] = v.strip()
            applied = True

    faqs = result.get("ai_expanded_faqs")
    if isinstance(faqs, list):
        clean = [{"question": str(f.get("question","")).strip(),
                  "answer": str(f.get("answer","")).strip()}
                 for f in faqs if isinstance(f, dict)
                 and f.get("question") and f.get("answer")]
        if clean:
            job["ai_expanded_faqs"] = clean
            job["ai_schema_faq"] = clean
            applied = True

    sd = result.get("ai_extracted_structured_data")
    if isinstance(sd, dict) and sd:
        job["ai_extracted_structured_data"] = sd
        applied = True

    return applied

def heal_structured_data(job, facts):
    """Fill missing structured data from facts (no API call needed)."""
    org_title = (facts.get("organization","") + " " + facts.get("location","")).upper()
    loc, pin = "India", "110001"
    for token, (state, pincode) in STATE_MAP.items():
        if token in org_title:
            loc, pin = state, pincode
            break

    # Last date from facts
    dates = facts.get("importantDates") or {}
    iso_date = ""
    for k, v in dates.items():
        if "last" in k.lower() or "closing" in k.lower():
            m = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', str(v))
            if m:
                iso_date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
                break
    if not iso_date:
        iso_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    sd = job.setdefault("ai_extracted_structured_data", {})
    if not sd.get("job_location"): sd["job_location"] = loc
    if not sd.get("postal_code"): sd["postal_code"] = pin
    if not sd.get("last_date") or sd["last_date"] in ("null","None",""):
        sd["last_date"] = iso_date
    if not sd.get("salary_range") or sd["salary_range"] in ("null","None","N/A",""):
        sd["salary_range"] = "21700 - 69100"

# ─────────────────────────────────────────────────────────────────────────────
# ATOMIC SAVE
# ─────────────────────────────────────────────────────────────────────────────
def save_json(master):
    """Har job ke baad save karo — atomic, crash-safe."""
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

# ─────────────────────────────────────────────────────────────────────────────
# JOB ITERATOR — ALL sources, FJA + sarkari + state + education
# ─────────────────────────────────────────────────────────────────────────────
def iter_all_jobs(master):
    """Yield (job_dict, source_label) from all sources."""
    # 1. FJA categories (structured format — most jobs)
    fja = master.get("freejobalert_categories") or {}
    if isinstance(fja, dict):
        for cat, jobs in fja.items():
            if isinstance(jobs, list):
                for j in jobs:
                    if isinstance(j, dict): yield j, f"fja:{cat}"

    # 2. Sarkari data (flat format)
    for j in (master.get("sarkari_data") or {}).get("jobs", []):
        if isinstance(j, dict): yield j, "sarkari"

    # 3. State jobs sections
    sj = master.get("state_jobs") or {}
    secs = sj.get("sections", []) if isinstance(sj, dict) else []
    for sec in secs:
        if isinstance(sec, dict):
            for j in sec.get("items", []):
                if isinstance(j, dict): yield j, "state"

    # 4. Education jobs
    ej = master.get("education_jobs") or {}
    if isinstance(ej, list):
        for j in ej:
            if isinstance(j, dict): yield j, "education"
    elif isinstance(ej, dict):
        for sec in ej.get("sections", []):
            if isinstance(sec, dict):
                for j in sec.get("items", []):
                    if isinstance(j, dict): yield j, "education"

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 56)
    print("🌙 TSJ AI Content Layer v3.0 — Nightly Batch Mode")
    print("=" * 56)
    print(f"   Model      : {MODEL}")
    print(f"   Rate       : {SAFE_RPM} RPM = {DELAY_SEC:.0f}s delay")
    print(f"   Daily limit: {DAILY_LIMIT} API calls")
    print(f"   Run limit  : {RUN_LIMIT} jobs this run")
    print(f"   Force regen: {FORCE_REGEN}")
    print()

    if not GROQ_KEY:
        print("❌ GROQ_API_KEY not set!")
        print("   Add to GitHub: Settings → Secrets → GROQ_API_KEY")
        sys.exit(1)

    if not os.path.exists(DATA_FILE):
        print(f"❌ {DATA_FILE} not found")
        sys.exit(1)

    # Load progress
    progress = load_progress()
    calls_today = progress["calls_today"]
    processed_today = set(progress["processed_slugs"])
    print(f"📊 Today's progress: {calls_today} calls done, {len(processed_today)} slugs processed")

    if calls_today >= DAILY_LIMIT:
        print(f"⚠️  Daily limit ({DAILY_LIMIT}) already reached. Run again tomorrow.")
        sys.exit(0)

    # Load master JSON
    master = json.load(open(DATA_FILE, encoding="utf-8"))

    # Stats
    generated = 0
    skipped_done = 0
    skipped_no_title = 0
    errors = 0

    for job, source in iter_all_jobs(master):

        # Hard stops
        if generated >= RUN_LIMIT:
            print(f"\n🔴 RUN_LIMIT ({RUN_LIMIT}) reached — stopping. Resume next run.")
            break
        if calls_today >= DAILY_LIMIT:
            print(f"\n🔴 DAILY_LIMIT ({DAILY_LIMIT}) reached — resuming tomorrow.")
            break

        title = get_title(job)
        if not title:
            skipped_no_title += 1
            continue

        slug = get_slug(job)
        new_hash = compute_hash(job)

        # Skip if already done
        if is_already_done(job, new_hash):
            skipped_done += 1
            continue

        # Also skip if processed in this run's progress (cross-source dup)
        if slug and slug in processed_today and not FORCE_REGEN:
            skipped_done += 1
            continue

        # Always heal structured data (fast, no API)
        facts = normalize_facts(job)
        heal_structured_data(job, facts)

        print(f"\n⚡ [{generated+1}/{RUN_LIMIT}] [{calls_today+1}/{DAILY_LIMIT}]")
        print(f"   {title[:65]}...")
        print(f"   Source: {source}")

        result = call_groq(facts)

        if result and apply_result(job, result):
            heal_structured_data(job, facts)  # re-fill any nulls AI left
            job["content_hash"] = new_hash
            job["ai_generated_at"] = datetime.now().strftime("%Y-%m-%d")

            generated += 1
            calls_today += 1
            if slug:
                processed_today.add(slug)

            # Atomic save after EACH job
            save_json(master)
            print(f"   ✅ Done — saved (total this run: {generated})")

            # Update progress
            progress["calls_today"] = calls_today
            progress["processed_slugs"] = list(processed_today)
            save_progress(progress)

        else:
            errors += 1
            print(f"   ⚠️  API returned nothing — skipping")

        # Rate limit delay
        time.sleep(DELAY_SEC)

    # Final save
    save_json(master)

    print(f"\n{'=' * 56}")
    print("📊 Run Summary")
    print(f"{'=' * 56}")
    print(f"  ✅ Generated this run : {generated}")
    print(f"  ⏭️  Skipped (done)     : {skipped_done}")
    print(f"  ❌ API errors         : {errors}")
    print(f"  📵 No title           : {skipped_no_title}")
    print(f"  📅 Total calls today  : {calls_today}/{DAILY_LIMIT}")
    print(f"\n  💾 JSON saved: {DATA_FILE}")

    # Count total enriched
    total_enriched = 0
    for j, _ in iter_all_jobs(master):
        if j.get("ai_overview") and len(j.get("ai_overview","")) > 50:
            total_enriched += 1
    print(f"  🌟 Total enriched so far: {total_enriched} jobs")
    print()

if __name__ == "__main__":
    main()
