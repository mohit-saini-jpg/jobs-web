#!/usr/bin/env python3
"""
ai_content_layer.py — Adds an AI-generated content layer on top of scraped facts.

Pipeline position (run AFTER merge, BEFORE the HTML generators):
    scraper_all.py → scraper_merge.py → ai_content_layer.py → generate_all.py

What it does (per the AI_CONTENT_LAYER_MASTER_PROMPT):
  1. Loads Complete_Jobs_Full_Data.json.
  2. Normalizes every job (across all 4 source shapes: SR / FJA / state / education)
     to ONE canonical fact-set.
  3. Computes a content_hash of the FACTS only.
  4. If the hash is unchanged from the last run → reuses existing ai_* fields
     (CACHE HIT, no API call). If changed/missing → queues an AI call (CACHE MISS).
  5. Moves old free-text fields into _backup_* (never rendered; the generator
     already hides any key starting with "_").
  6. Calls Gemini (free tier) sequentially, rate-limited, with backoff + a daily
     cap. On any failure the job simply keeps its _backup_* content (graceful
     degradation — never a broken page).
  7. Writes the same JSON back in place — additive only, schema-compatible.

SAFETY:
  - One request at a time (no parallelism for AI calls).
  - Respects Gemini free-tier limits (≈10-15 RPM, ≈1000-1500 RPD as of 2026).
  - --dry-run and --limit N for staged rollout.
  - Never alters a fact field. Never deletes _backup_*.

USAGE:
  export GEMINI_API_KEY=...                 # required for live calls
  python3 ai_content_layer.py --dry-run --limit 5     # preview prompts, no API, no write
  python3 ai_content_layer.py --limit 20              # process 20 jobs for real
  python3 ai_content_layer.py --category SR_Result    # only one category (staged rollout)
  python3 ai_content_layer.py                          # full run (rate-limited, resumable)
"""
import os
import sys
import json
import time
import hashlib
import argparse
from datetime import date

# ──────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────
DATA_FILE   = os.environ.get("AI_DATA_FILE", "data/Complete_Jobs_Full_Data.json")
USAGE_FILE  = "ai_usage_tracker.json"        # sidecar: requests/tokens today
MODEL       = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY     = os.environ.get("GEMINI_API_KEY", "")

# Free-tier limits (confirm live numbers in Google AI Studio; conservative defaults).
GEMINI_RPM_LIMIT  = int(os.environ.get("GEMINI_RPM", "15"))
SAFE_RPM          = max(1, int(GEMINI_RPM_LIMIT * 0.7))          # stay under the ceiling
MIN_DELAY_SECONDS = 60.0 / SAFE_RPM                              # ~6s between calls
DAILY_LIMIT       = int(os.environ.get("GEMINI_DAILY_LIMIT", "1000"))
BACKOFFS          = [10, 30, 60]                                 # 429 retry waits, then stop


# ──────────────────────────────────────────────────────────────────────────
# USAGE TRACKER (atomic sidecar, same pattern as incremental_cache.py)
# ──────────────────────────────────────────────────────────────────────────
def _load_usage():
    today = date.today().isoformat()
    if os.path.exists(USAGE_FILE):
        try:
            u = json.load(open(USAGE_FILE, encoding="utf-8"))
            if u.get("date") == today:
                return u
        except Exception:
            pass
    return {"date": today, "requests_today": 0, "tokens_today": 0}


def _save_usage(u):
    tmp = USAGE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(u, f, ensure_ascii=False)
    os.replace(tmp, USAGE_FILE)


# ──────────────────────────────────────────────────────────────────────────
# NORMALIZER — map each of the 4 source shapes to ONE canonical fact-set.
# This is the single source of truth for "what are the facts of this job".
# ──────────────────────────────────────────────────────────────────────────
def _first(d, *keys, default=""):
    for k in keys:
        v = (d or {}).get(k)
        if v not in (None, "", [], {}):
            return v
    return default


def normalize_facts(job, source):
    """Return a canonical fact dict regardless of source shape.
    source ∈ {'sarkari', 'fja', 'state', 'education'}"""
    if source == "sarkari":
        return {
            "title":           _first(job, "title"),
            "organization":    _first(job, "organization"),
            "totalPost":       _first(job, "totalPost"),
            "postDate":        _first(job, "postDate"),
            "importantDates":  _first(job, "importantDates", default={}),
            "applicationFee":  _first(job, "applicationFee", default={}),
            "ageLimit":        _first(job, "ageLimit", default={}),
            "vacancyDetails":  _first(job, "vacancyDetails", default=[]),
            "importantLinks":  _first(job, "importantLinks", default=[]),
            "category":        _first(job, "category"),
        }
    if source == "fja":
        bd = job.get("basic_details", {}) or {}
        return {
            "title":           _first(bd, "job_title", "post_name"),
            "organization":    _first(bd, "organization_name"),
            "totalPost":       _first(bd, "total_vacancies"),
            "postDate":        _first(bd, "post_date", "last_updated"),
            "importantDates":  _first(job, "important_dates", default={}),
            "applicationFee":  _first(job, "application_fee", default={}),
            "ageLimit":        _first(job, "age_limit", default={}),
            "vacancyDetails":  _first(job, "vacancy_details", default=[]),
            "importantLinks":  _first(job, "important_links", default=[]),
            "category":        "",
        }
    # state / education: real data sits inside item["detail"], list-level has summary
    detail = job.get("detail", {}) or {}
    bd = detail.get("basic_details", {}) or {}
    return {
        "title":           _first(job, "name") or _first(bd, "job_title", "post_name"),
        "organization":    _first(job, "board") or _first(bd, "organization_name"),
        "totalPost":       _first(bd, "total_vacancies"),
        "postDate":        _first(job, "postDate") or _first(bd, "post_date"),
        "importantDates":  _first(detail, "important_dates", default={}),
        "applicationFee":  _first(detail, "application_fee", default={}),
        "ageLimit":        _first(detail, "age_limit", default={}),
        "vacancyDetails":  _first(detail, "vacancy_details", default=[]),
        "importantLinks":  _first(detail, "important_links", default=[]),
        "category":        _first(job, "category"),
    }


# ──────────────────────────────────────────────────────────────────────────
# CONTENT HASH — hash of FACTS only, so AI is re-run only when facts change.
# ──────────────────────────────────────────────────────────────────────────
def compute_content_hash(facts):
    keyed = {
        "title":          facts.get("title", ""),
        "totalPost":      facts.get("totalPost", ""),
        "importantDates": facts.get("importantDates", {}),
        "applicationFee": facts.get("applicationFee", {}),
        "vacancyDetails": facts.get("vacancyDetails", []),
        "ageLimit":       facts.get("ageLimit", {}),
    }
    blob = json.dumps(keyed, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(blob.encode("utf-8")).hexdigest()


# ──────────────────────────────────────────────────────────────────────────
# BACKUP MIGRATION — move free-text fields into _backup_* (one-time per job).
# Generator already hides any key starting with "_", so these never render.
# ──────────────────────────────────────────────────────────────────────────
def migrate_backups(job, source):
    if source in ("sarkari", "fja"):
        si_keys  = ("shortInfo", "short_information")
        faq_keys = ("faq", "faqs")
        hta_keys = ("how_to_apply", "howToApply")
        target = job
        if source == "fja":
            target_bd = job.get("basic_details", {}) or {}
            for k in si_keys:
                if target_bd.get(k) and "_backup_short_info" not in job:
                    job["_backup_short_info"] = target_bd.get(k)
                    break
        for k in si_keys:
            if target.get(k) and "_backup_short_info" not in job:
                job["_backup_short_info"] = target.get(k)
                break
        for k in faq_keys:
            if target.get(k) and "_backup_faqs" not in job:
                job["_backup_faqs"] = target.get(k)
                break
        for k in hta_keys:
            if target.get(k) and "_backup_how_to_apply" not in job:
                job["_backup_how_to_apply"] = target.get(k)
                break
    else:
        detail = job.get("detail", {}) or {}
        if detail.get("short_information") and "_backup_short_info" not in job:
            job["_backup_short_info"] = detail.get("short_information")
        if detail.get("faq") and "_backup_faqs" not in job:
            job["_backup_faqs"] = detail.get("faq")
        if detail.get("how_to_apply") and "_backup_how_to_apply" not in job:
            job["_backup_how_to_apply"] = detail.get("how_to_apply")


# ──────────────────────────────────────────────────────────────────────────
# AI PLACEHOLDERS — ensure the ai_* keys exist (null) so the schema is stable
# even before/without a successful AI call.
# ──────────────────────────────────────────────────────────────────────────
AI_TEXT_KEYS = [
    "ai_h1", "ai_title", "ai_meta_description", "ai_overview",
    "ai_expert_analysis", "ai_who_should_apply", "ai_preparation_tips",
    "ai_salary_insights", "ai_job_profile_analysis", "ai_selection_strategy",
    "ai_how_to_apply_rewrite",
]


def ensure_ai_placeholders(job):
    for k in AI_TEXT_KEYS:
        job.setdefault(k, None)
    job.setdefault("ai_expanded_faqs", [])
    job.setdefault("ai_schema_faq", [])
    job.setdefault("ai_extracted_structured_data",
                   {"last_date": None, "salary_range": None,
                    "total_vacancies": None, "job_location": None})
    job.setdefault("content_hash", "")


# ──────────────────────────────────────────────────────────────────────────
# GEMINI PROMPT + CALL
# ──────────────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """You are a Sarkari Naukri content editor. Using ONLY the facts in INPUT_FACTS below, write original Hinglish content for a government-jobs listing page.

STRICT RULES:
1. Do not invent or alter any date, number, fee amount, or URL.
2. If a fact is missing from INPUT_FACTS, do not guess it — omit that detail rather than fabricate it.
3. Write in natural Hinglish (Hindi-English mix), the way a human editor writing for Indian job-seekers would.
4. Vary sentence structure and phrasing — do not reuse the same opening template.
5. Output ONLY valid JSON, no markdown fences, no preamble.

INPUT_FACTS:
{facts_json}

OUTPUT — exactly these keys:
{{
  "ai_h1": "(<=60 chars)",
  "ai_title": "(<=60 chars)",
  "ai_meta_description": "(<=160 chars, include the last date if known)",
  "ai_overview": "(200-250 words)",
  "ai_expert_analysis": "(150-200 words)",
  "ai_who_should_apply": "(100-150 words)",
  "ai_preparation_tips": "(100-150 words, concrete)",
  "ai_salary_insights": "(100-150 words; say 'as per official notification' if figures absent)",
  "ai_job_profile_analysis": "(100-150 words)",
  "ai_selection_strategy": "(100-150 words)",
  "ai_how_to_apply_rewrite": "(150-200 words, natural paragraph)",
  "ai_expanded_faqs": [{{"question":"(Hinglish)","answer":"(Hinglish, specific)"}}],
  "ai_extracted_structured_data": {{"last_date":null,"salary_range":null,"total_vacancies":null,"job_location":null}}
}}
Generate 6-8 FAQs in ai_expanded_faqs."""


def build_prompt(facts):
    return PROMPT_TEMPLATE.format(
        facts_json=json.dumps(facts, ensure_ascii=False, indent=2))


def call_gemini(prompt):
    """Single sequential Gemini call. Returns parsed dict or None on failure.
    Uses the REST endpoint so no SDK dependency is required."""
    import urllib.request
    import urllib.error

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent?key={API_KEY}")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "response_mime_type": "application/json"},
    }
    data = json.dumps(body).encode("utf-8")

    for attempt, wait in enumerate([0] + BACKOFFS):
        if wait:
            print(f"      [backoff] waiting {wait}s before retry...")
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, data=data,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            text = (payload["candidates"][0]["content"]["parts"][0]["text"]).strip()
            # strip accidental markdown fences
            if text.startswith("```"):
                text = text.split("```", 2)[1] if "```" in text[3:] else text
                text = text.lstrip("json").strip().strip("`").strip()
            return json.loads(text)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                if attempt < len(BACKOFFS):
                    continue          # retry with next backoff
                print("      [429] daily/rate quota — stopping AI for this run.")
                return "QUOTA_STOP"
            print(f"      [HTTP {e.code}] {e.reason} — skipping this job.")
            return None
        except Exception as e:
            print(f"      [error] {e} — skipping this job.")
            return None
    return None


def apply_ai_result(job, result):
    """Merge AI output into the job, ONLY into ai_* keys. Never touches facts."""
    if not isinstance(result, dict):
        return False
    for k in AI_TEXT_KEYS:
        if result.get(k):
            job[k] = result[k]
    if isinstance(result.get("ai_expanded_faqs"), list):
        job["ai_expanded_faqs"] = result["ai_expanded_faqs"]
        # mirror into schema FAQ for JSON-LD
        job["ai_schema_faq"] = result["ai_expanded_faqs"]
    if isinstance(result.get("ai_extracted_structured_data"), dict):
        job["ai_extracted_structured_data"] = result["ai_extracted_structured_data"]
    return True


# ──────────────────────────────────────────────────────────────────────────
# JOB ITERATOR — yields (job_dict, source) for every job across all 4 sources.
# We yield the live dict reference so edits write back into the loaded JSON.
# ──────────────────────────────────────────────────────────────────────────
def iter_jobs(m, only_category=None):
    for j in m.get("sarkari_data", {}).get("jobs", []):
        if only_category and j.get("category") != only_category:
            continue
        yield j, "sarkari"
    for cat, jobs in m.get("freejobalert_categories", {}).items():
        if only_category and cat != only_category:
            continue
        if isinstance(jobs, list):
            for j in jobs:
                yield j, "fja"
    for sec in m.get("state_jobs", {}).get("sections", []):
        for j in sec.get("items", []):
            yield j, "state"
    for sec in m.get("education_jobs", {}).get("sections", []):
        for j in sec.get("items", []):
            yield j, "education"


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="preview prompts + cache decisions, no API calls, no write")
    ap.add_argument("--limit", type=int, default=0,
                    help="process at most N cache-miss jobs (0 = no limit)")
    ap.add_argument("--category", default=None,
                    help="only process this category (staged rollout)")
    args = ap.parse_args()

    if not os.path.exists(DATA_FILE):
        print(f"ERROR: {DATA_FILE} not found.")
        sys.exit(1)

    m = json.load(open(DATA_FILE, encoding="utf-8"))

    usage = _load_usage()
    print(f"AI Content Layer — model={MODEL} | today's requests so far: "
          f"{usage['requests_today']}/{DAILY_LIMIT}")
    if args.dry_run:
        print("DRY RUN — no API calls, no file write.\n")
    if not API_KEY and not args.dry_run:
        print("ERROR: GEMINI_API_KEY not set. Use --dry-run to preview, or set the key.")
        sys.exit(1)

    cache_hits = cache_miss = generated = skipped_quota = 0
    processed = 0
    quota_stop = False

    for job, source in iter_jobs(m, only_category=args.category):
        ensure_ai_placeholders(job)
        migrate_backups(job, source)

        facts = normalize_facts(job, source)
        if not facts.get("title"):
            continue   # nothing to work with

        new_hash = compute_content_hash(facts)

        # CACHE HIT: facts unchanged AND we already have AI content
        if job.get("content_hash") == new_hash and job.get("ai_overview"):
            cache_hits += 1
            continue

        cache_miss += 1
        slug = facts["title"][:50]
        print(f"  [AI CACHE MISS] {source}/{slug}")

        if args.dry_run:
            if args.limit and cache_miss > args.limit:
                break
            continue

        if quota_stop:
            skipped_quota += 1
            continue

        # daily-cap guard
        if usage["requests_today"] >= DAILY_LIMIT:
            print("  [DAILY LIMIT REACHED] — keeping _backup_* content for the rest.")
            quota_stop = True
            skipped_quota += 1
            continue
        # slow down at 80%
        delay = MIN_DELAY_SECONDS * (2 if usage["requests_today"] >= 0.8 * DAILY_LIMIT else 1)

        prompt = build_prompt(facts)
        result = call_gemini(prompt)
        usage["requests_today"] += 1
        _save_usage(usage)

        if result == "QUOTA_STOP":
            quota_stop = True
            skipped_quota += 1
            continue
        if result and apply_ai_result(job, result):
            job["content_hash"] = new_hash
            generated += 1
            print(f"      ✓ generated ({generated})")
        # else: job keeps its _backup_* content (graceful degradation)

        processed += 1
        if args.limit and processed >= args.limit:
            print(f"  --limit {args.limit} reached, stopping.")
            break
        time.sleep(delay)

    print(f"\nSummary: cache_hits={cache_hits} cache_miss={cache_miss} "
          f"generated={generated} skipped_quota={skipped_quota}")

    if not args.dry_run:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)
        print(f"Wrote {DATA_FILE} (additive ai_* fields, facts untouched).")
    else:
        print("Dry run complete — no file written.")


if __name__ == "__main__":
    main()
