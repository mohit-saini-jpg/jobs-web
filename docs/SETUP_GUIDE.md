# Daily Scraper + AI Layer — Complete Setup Guide

Bhai, ab poora system automated hoga. Har din sabkuch apne-aap chalega, quota track hoga, site update hoga.

---

## 📋 PART 1 — Files kahan rakhni hain (file-by-file)

| File | Path | Kya hai |
|---|---|---|
| `ai_content_layer.py` | `scraper/ai_content_layer.py` | AI layer main script |
| `generate_all.py` | `site/jobs-web-main/generate_all.py` | Site generator (REPLACE) |
| **Daily workflow** | `.github/workflows/daily_scraper_ai.yml` | GitHub Actions (NAI FILE, nayi folder) |
| **Monitor script** | `ai_quota_monitor.py` | Quota tracking + dashboard |
| **History file** (auto-created) | `ai_daily_usage_history.json` | Usage log (git me track karo) |

### Setup Step 1 — Workflow file rakh do
```
apna-repo-root/
├── .github/
│   └── workflows/
│       └── daily_scraper_ai.yml   ← IDHAR RAKH DO (nai file)
├── scraper/
│   ├── ai_content_layer.py
│   └── ...
├── site/
│   └── jobs-web-main/
│       └── generate_all.py
└── ai_quota_monitor.py
```

**Key point:** `.github/workflows/` folder **pehle se exist karta hoga**. Usmei `daily_scraper_ai.yml` file create karo (ya rename the uploaded file).

---

## 🔐 PART 2 — GitHub Secrets setup (already done, verify karo)

1. GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Check: `GEMINI_API_KEY` naam se secret dikh raha hai?
   - ✅ Dikh raha → theek hai, aage badho
   - ❌ Nahi dikh raha → "New repository secret" pe click karke add karo

---

## 🚀 PART 3 — System kaise chalega (daily automatic)

### Timing
- **Default:** har roz **2 AM IST** (8:30 PM UTC) automatic run
- GitHub Actions automatic run karega (tume kuch nahi karna)

### Ya manual trigger karna ho to
```bash
# GitHub web UI se: Actions tab → Daily Scraper + AI Content Layer → Run workflow
# Ya command line se:
gh workflow run daily_scraper_ai.yml
```

---

## 📊 PART 4 — Quota tracking + Dashboard (daily check)

### Command 1 — Aaj ke status
```bash
python3 ai_quota_monitor.py
```
Output:
```
══════════════════════════════════════════════════════
  AI CONTENT LAYER — TODAY'S STATUS
══════════════════════════════════════════════════════
  Date:              2026-06-18
  API Requests:      234 / 1000
  Remaining:         766
  Usage:               23.4%

  Jobs with AI:        234 / 5432
  Progress:            4.3%
  Estimate:            ~23 more days (complete by 2026-07-11)
══════════════════════════════════════════════════════
```

### Command 2 — Last 30 days history
```bash
python3 ai_quota_monitor.py --history
```
Output:
```
══════════════════════════════════════════════════════
  AI QUOTA HISTORY — Last 30 days
══════════════════════════════════════════════════════
  Date         Requests        % of 1000       Cumulative
──────────────────────────────────────────────────────
  2026-06-18     234/1000        23.4%           234
  Average per day: 234 requests
  Total so far: 234 requests
══════════════════════════════════════════════════════
```

### Command 3 — Estimate (kab complete hoga)
```bash
python3 ai_quota_monitor.py --estimate
```
Output:
```
══════════════════════════════════════════════════════
  COMPLETION ESTIMATE
══════════════════════════════════════════════════════
  Total jobs:        5432
  With AI content:   234
  Remaining:         5198
  
  Daily average:     234 requests/day
  Days to complete:  ~23 days
  Est. complete by:  2026-07-11
══════════════════════════════════════════════════════
```

---

## 🔄 PART 5 — 5000+ jobs ke liye kaise hoga (step-by-step progress)

**Scenario:** Aapke 5432 jobs hain, daily API limit 1000 hai.

| Day | Jobs Processed | Total With AI | Remaining | Status |
|---|---|---|---|---|
| Day 1 | 1000 | 1000 | 4432 | ✅ Processing |
| Day 2 | 1000 | 2000 | 3432 | ✅ Processing |
| Day 3 | 1000 | 3000 | 2432 | ✅ Processing |
| Day 4 | 1000 | 4000 | 1432 | ✅ Processing |
| Day 5 | 1000 | 5000 | 432 | ✅ Processing |
| Day 6 | 432 | 5432 | 0 | ✅ **COMPLETE** |

**Key points:**
- Din 1-5: har din 1000 jobs process hongi (limit ke karan)
- Din 6: baaki 432 jobs + koi bhi naye/changed jobs
- **Baaki din**: sirf naye/changed jobs AI get karengi (cache ki wajah se zero API calls for unchanged facts)

---

## ⚠️ PART 6 — Important safeguards aur monitoring

### 1. Daily run fail ho jaye (internet issue, etc.)
```
Kya hoga:
✅ Next day automatic dobara run hoga
✅ Cache rahta hai — same data dobara process nahi hoga
✅ Site pichle din wala hi generate rehta hai (broken page nahi)
```

### 2. API quota exhaust ho gaya mid-day
```
Workflow log me dikhega: "⚠️ Daily quota exhausted"
✅ Baaki jobs ke liye _backup_* content use hota hai
✅ Site normal generate ho jaata hai
✅ Next day phir se shuru
```

### 3. Kisi category ki AI quality kharab lage
```
Turant revert:
1. GitHub repo me jaao
2. wo jobs ke ai_* fields delete karo (OR .gitignore se exclude karke git reset)
3. _backup_* content still intact hai, usse fallback hota hai
4. Next run ai_* fields phir generate hogi
```

---

## 🛠️ PART 7 — Manual controls (jab chahiye custom runs)

### Custom run — sirf ek category
```bash
cd scraper
export GEMINI_API_KEY="apni-key"
python3 ai_content_layer.py --category SR_Result --limit 100
```

### Dry run — kuch change nahi, sirf preview
```bash
python3 ai_content_layer.py --dry-run --limit 10
```

### Site regenerate (without new AI data)
```bash
cd site/jobs-web-main
python3 generate_all.py
```

---

## 📈 PART 8 — Monitoring checklist (daily)

| Task | Frequency | Kya check karna |
|---|---|---|
| Quota status | Daily | `python3 ai_quota_monitor.py` — remaining quota check |
| Job pages sample | Weekly | 3-5 random job pages khol aur AI content dekh |
| Errors | Daily | GitHub Actions logs (fail ho to automatically alert aayega) |
| Progress | Weekly | `--estimate` command se timeline check |
| Data integrity | Monthly | 10 random jobs manually check — facts unchanged? |

---

## 🎯 PART 9 — Success checklist (sab theek hai iska matlab)

- ✅ GitHub Actions "Daily Scraper + AI Content Layer" workflow visible aur enabled
- ✅ `GEMINI_API_KEY` secret set ho
- ✅ `ai_quota_monitor.py` command run hoke status dikhaye
- ✅ har din around 1000 jobs AI content get kar rahe hain
- ✅ 5-6 din baad sab 5000+ jobs ke paas AI content hoga
- ✅ Job pages pe AI Overview, Expert Analysis, AI FAQ dikh rahe hain
- ✅ Fact tables (vacancy, dates, fees) **unchanged** hain
- ✅ Site normally generate ho raha hai (koi errors nahi)

---

## 🚨 Troubleshooting

### Problem: Workflow run ho raha par errors aa rahe hain
**Solution:**
1. GitHub Actions tab → logs dekh
2. Agar `GEMINI_API_KEY` error — secret properly set hai check karo
3. Agar `ai_content_layer.py not found` — file path sahi hai check karo
4. Manual trigger karo to pata lag jaayega exact error

### Problem: API quota bahut fast exhaust ho raha
**Solution:**
- This is normal! 1000/day ke hisaab se ye 5-6 din me complete hoga
- Agar project prod hai aur jaldi chahiye to Gemini free se paid tier upgrade karo
- Paid tier me unlimited use kar sakta hai (cost: ~$0.10 per million tokens)

### Problem: Cache nahi lag raha (har bar API call ho raha)
**Solution:**
- `content_hash` set ho check karo (pehla run me sab new hote hain)
- 2nd day se cache hit hone lagna chahiye
- Facts change na ho tab cache kaam karta hai

### Problem: AI content kharab quality ka dikh raha
**Solution:**
1. Pehle check: fact fields (dates, numbers) bilkul sahi hain?
   - Agar facts hi galat hain to ye scraper ki issue hai, AI ki nahi
2. Text quality kharab:
   - TEMPORARY: uske liye output sa backup data se revert kar
   - PERMANENT: malum karo kis category ko issue hai, phase out karo

---

## 📝 Git setup (.gitignore update)

Add these to your `.gitignore` (agar nahi hain):
```
# AI layer temp files
scraper/scrape_seen_urls.json
scraper/scraper_checkpoint.json
scraper/ai_usage_tracker.json

# But DO track these:
# ai_daily_usage_history.json (keep for monitoring)
# Complete_Jobs_Full_Data.json (keep, it's your data)
```

---

## Quick Summary

| Step | Command | Frequency |
|---|---|---|
| Manual check | `python3 ai_quota_monitor.py` | Daily |
| Manual run (optional) | `python3 ai_content_layer.py --category X` | As needed |
| Automatic run | (GitHub Actions) | Daily 2 AM IST |
| Completion estimate | `python3 ai_quota_monitor.py --estimate` | Weekly |

**Timeline: 5-6 din me 5000+ jobs fully processed ho jayenge. Iske baad sirf naye jobs + changed facts ko AI call chalega (zero overhead).**

