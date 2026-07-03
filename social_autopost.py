"""
social_autopost.py
-------------------
Free auto-posting module for X (Twitter) and Telegram.

Designed to be imported and called at the END of generate_all.py, after
new jobs have been written to Complete_Jobs_Full_Data.json.

Install deps (one time):
    pip install tweepy requests

Usage from generate_all.py:

    from social_autopost import autopost_new_jobs

    if __name__ == "__main__":
        # ... existing site generation code ...
        autopost_new_jobs(all_jobs)   # all_jobs = list of job dicts

Each job dict is expected to have at least:
    job["_canonical_slug"] (or "slug")  -> used to build OUR OWN site URL
    job["title"]                        -> job title / post name

NOTE: We never post job["url"] / job["sourceUrl"] etc. — on this project those
point to the official/source site, not topsarkarijobs.com. The link that gets
posted is always built as: https://www.topsarkarijobs.com/jobs/{slug}/
See get_own_site_url() below.
"""

import os
import json
import time
import html
import re
import requests

# ── Optional import: tweepy (only needed for X/Twitter posting) ─────────────
try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False


# =============================================================================
# CONFIG — fill these in (env vars recommended over hardcoding)
# =============================================================================

# ---- X (Twitter) — OAuth 1.0a User Context (Read + Write) ----
X_CONSUMER_KEY = os.environ.get("X_CONSUMER_KEY", "YOUR_CONSUMER_KEY")
X_CONSUMER_SECRET = os.environ.get("X_CONSUMER_SECRET", "YOUR_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "YOUR_ACCESS_TOKEN_SECRET")

# ---- Telegram ----
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHANNEL_USERNAME = os.environ.get("TELEGRAM_CHANNEL_USERNAME", "@TopSarkariJobs")

# ---- Dedup tracking file ----
POSTED_JOBS_FILE = "posted_jobs.txt"

# ---- Field name for the job title in your job dict ----
JOB_TITLE_FIELD = "title"

# ---- YOUR site's base URL (must match BASE_URL in generate_all.py) ----
SITE_BASE_URL = "https://www.topsarkarijobs.com"

# Fields that might hold a source/official-site link. We NEVER post these directly —
# they're only checked so we can warn you if a job is missing a usable slug.
_SOURCE_LEAK_FIELDS = ("url", "sourceUrl", "source_url", "apply_link", "official_link")

# ---- Behavior ----
SITE_NAME = "TopSarkariJobs"
DELAY_BETWEEN_POSTS_SECONDS = 2   # be gentle with rate limits when posting many jobs at once
MAX_JOBS_PER_RUN = 20             # safety cap so a huge new-jobs batch doesn't spam-post everything at once


# =============================================================================
# Own-site URL builder
# =============================================================================
#
# IMPORTANT: We deliberately build the link ourselves from the job's slug
# instead of trusting any "url" field in the JSON — on this project, job['url']
# / job['sourceUrl'] etc. point to the OFFICIAL/source site (e.g. sarkariresult.com,
# esb.mp.gov.in), not to our own pages. Posting those would send readers straight
# to the source and give topsarkarijobs.com zero traffic.
#
# This mirrors get_canonical_slug() in generate_all.py:
#   Priority 1: job['_canonical_slug']  (scraper-set, permanent — same as site)
#   Priority 2: job['slug']             (raw scraper slug)
#   Priority 3: job['filename']         (fallback, if present)
# If none of these exist, the job is skipped (never falls back to a source URL).

def _norm_slug(s):
    """Mirrors _norm_slug() in generate_all.py EXACTLY — must stay in sync.
    Lowercases, converts spaces/underscores to dashes, collapses repeated
    dashes, strips leading/trailing dashes, and truncates to 80 chars (the
    same limit generate_all.py uses when writing /jobs/{slug}/ folders)."""
    if not s:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")[:80].strip("-")


def get_own_site_url(job):
    """
    Build the canonical topsarkarijobs.com detail-page URL for a job,
    matching the /jobs/{slug}/ pattern used by generate_all.py.
    Returns None if no usable slug can be found (job is skipped, not posted).
    """
    raw_slug = (
        str(job.get("_canonical_slug") or "").strip()
        or str(job.get("slug") or "").strip()
        or str(job.get("filename") or "").strip()
    )
    if not raw_slug:
        return None

    # Strip SR category prefix (sr_result-, sr_admit_card-, etc.) and a
    # trailing hex hash — same cleanup generate_all.py applies to raw slugs
    # (only relevant for Priority-2/3 fallback; _canonical_slug is already clean).
    if not job.get("_canonical_slug"):
        raw_slug = re.sub(r"^sr_[a-z_]+-", "", raw_slug)
        _tail = re.search(r"-([0-9a-f]{6,8})$", raw_slug)
        if _tail and not _tail.group(1).isdigit():
            raw_slug = raw_slug[: -len(_tail.group(0))]

    slug = _norm_slug(raw_slug)
    if not slug:
        return None

    return f"{SITE_BASE_URL}/jobs/{slug}/"


def _warn_if_source_url_only(job):
    """Log a warning (does not raise) if a job has no slug but does have a
    source/official link — so you notice a job that would otherwise be silently
    skipped instead of accidentally posting the wrong link."""
    for field in _SOURCE_LEAK_FIELDS:
        if job.get(field):
            title = job.get(JOB_TITLE_FIELD, "Unknown job")
            print(f"[AutoPost] WARNING: '{title}' has no _canonical_slug/slug but "
                  f"has a '{field}' field pointing off-site. Skipping instead of "
                  f"posting a source-site link.")
            return


# =============================================================================
# Dedup helpers
# =============================================================================

def _load_posted_urls():
    """Return a set of job URLs that have already been posted."""
    if not os.path.exists(POSTED_JOBS_FILE):
        return set()
    with open(POSTED_JOBS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def _mark_as_posted(url):
    """Append a URL to the posted-jobs tracking file."""
    with open(POSTED_JOBS_FILE, "a", encoding="utf-8") as f:
        f.write(url.strip() + "\n")


# =============================================================================
# X (Twitter) posting
# =============================================================================

def _get_twitter_client():
    """
    Build a tweepy Client using OAuth 1.0a user context.
    Returns None if tweepy isn't installed or keys are missing.
    """
    if not TWEEPY_AVAILABLE:
        print("[X] tweepy not installed — skipping X posting. Run: pip install tweepy")
        return None

    if "YOUR_" in (X_CONSUMER_KEY + X_CONSUMER_SECRET + X_ACCESS_TOKEN + X_ACCESS_TOKEN_SECRET):
        print("[X] Twitter keys not configured — skipping X posting.")
        return None

    try:
        client = tweepy.Client(
            consumer_key=X_CONSUMER_KEY,
            consumer_secret=X_CONSUMER_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
        )
        return client
    except Exception as e:
        print(f"[X] Failed to initialize Twitter client: {e}")
        return None


def post_to_twitter(client, title, url):
    """
    Post a single job update to X. Returns True on success, False on failure.
    Never raises — all errors are caught and logged so the main pipeline continues.
    """
    if client is None:
        return False

    tweet_text = f"🚨 {title}\n\nApply now 👇\n{url}\n\n#SarkariJobs #{SITE_NAME.replace(' ', '')}"
    # Twitter's hard cap is 280 chars — trim the title if needed
    if len(tweet_text) > 280:
        overflow = len(tweet_text) - 280
        title = title[: max(0, len(title) - overflow - 3)] + "..."
        tweet_text = f"🚨 {title}\n\nApply now 👇\n{url}\n\n#SarkariJobs #{SITE_NAME.replace(' ', '')}"

    try:
        client.create_tweet(text=tweet_text)
        print(f"[X] Posted: {title}")
        return True
    except Exception as e:
        # 401 here almost always means the Access Token/Secret were generated
        # BEFORE the app's permission was set to "Read and Write" — regenerate
        # them from the X Developer Portal after confirming Read+Write is on.
        print(f"[X] Failed to post '{title}': {e}")
        return False


# =============================================================================
# Telegram posting
# =============================================================================

def post_to_telegram(title, url):
    """
    Post a single job update to a Telegram channel via the Bot API.
    Returns True on success, False on failure. Never raises.
    """
    if "YOUR_" in TELEGRAM_BOT_TOKEN:
        print("[Telegram] Bot token not configured — skipping Telegram posting.")
        return False

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Telegram's HTML parse_mode requires <, >, & to be escaped or the whole
    # request is rejected with 400 Bad Request: can't parse entities.
    safe_title = html.escape(title)
    message = f"🚨 <b>{safe_title}</b>\n\nApply now: {url}"

    payload = {
        "chat_id": TELEGRAM_CHANNEL_USERNAME,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(api_url, data=payload, timeout=15)
        if not response.ok:
            # Print Telegram's actual error description (e.g. "chat not found",
            # "bot was blocked", "not enough rights to post") — this is the
            # single most useful line for debugging a failed post.
            print(f"[Telegram] API error {response.status_code} for '{title}': {response.text}")
            return False
        result = response.json()
        if result.get("ok"):
            print(f"[Telegram] Posted: {title}")
            return True
        else:
            print(f"[Telegram] API returned failure for '{title}': {result}")
            return False
    except Exception as e:
        print(f"[Telegram] Failed to post '{title}': {e}")
        return False


# =============================================================================
# Main entry point
# =============================================================================

def autopost_new_jobs(jobs):
    """
    Main function to call from generate_all.py.

    jobs: list of job dicts (e.g. loaded from Complete_Jobs_Full_Data.json)

    For every job not already in posted_jobs.txt:
        - attempts to post to X
        - attempts to post to Telegram
        - if EITHER succeeds, marks the job URL as posted
          (change to "if BOTH succeed" below if you want stricter dedupe)
    """
    if not jobs:
        print("[AutoPost] No jobs provided — nothing to post.")
        return

    posted_urls = _load_posted_urls()
    twitter_client = _get_twitter_client()

    # Build (job, own_site_url) pairs, skipping jobs that have no usable slug
    # and jobs whose own-site URL has already been posted.
    candidates = []
    for j in jobs:
        own_url = get_own_site_url(j)
        if own_url is None:
            _warn_if_source_url_only(j)
            continue
        if own_url in posted_urls:
            continue
        candidates.append((j, own_url))

    if not candidates:
        print("[AutoPost] No new jobs to post — all already posted (or no slugs found).")
        return

    if len(candidates) > MAX_JOBS_PER_RUN:
        print(f"[AutoPost] {len(candidates)} new jobs found, capping this run to {MAX_JOBS_PER_RUN}.")
        candidates = candidates[:MAX_JOBS_PER_RUN]

    print(f"[AutoPost] Posting {len(candidates)} new job(s)...")

    for job, url in candidates:
        title = job.get(JOB_TITLE_FIELD, "New Sarkari Job Alert")

        x_ok = False
        tg_ok = False

        # --- X (Twitter) ---
        try:
            x_ok = post_to_twitter(twitter_client, title, url)
        except Exception as e:
            # extra safety net on top of the try/except already inside post_to_twitter
            print(f"[AutoPost] Unexpected X error for '{title}': {e}")

        # --- Telegram ---
        try:
            tg_ok = post_to_telegram(title, url)
        except Exception as e:
            print(f"[AutoPost] Unexpected Telegram error for '{title}': {e}")

        # Mark as posted if at least one channel succeeded
        if x_ok or tg_ok:
            _mark_as_posted(url)
        else:
            print(f"[AutoPost] Both X and Telegram failed for '{title}' — will retry next run.")

        time.sleep(DELAY_BETWEEN_POSTS_SECONDS)

    print("[AutoPost] Done.")


# =============================================================================
# Standalone test / manual run
# =============================================================================

if __name__ == "__main__":
    # Quick manual test using Complete_Jobs_Full_Data.json if present in the same folder
    data_file = "Complete_Jobs_Full_Data.json"
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            all_jobs = json.load(f)
        # If your JSON is a dict of categories rather than a flat list, flatten it first, e.g.:
        # all_jobs = [job for category in all_jobs.values() for job in category]
        autopost_new_jobs(all_jobs)
    else:
        print(f"'{data_file}' not found. Run this from generate_all.py instead, "
              f"passing your jobs list directly to autopost_new_jobs().")
