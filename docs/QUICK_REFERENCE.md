# Quick Reference Card — Daily AI Layer Operations

## 🚀 ONE-LINE COMMANDS (copy-paste ready)

### Check today's status
```bash
python3 ai_quota_monitor.py
```

### Check history (last 30 days)
```bash
python3 ai_quota_monitor.py --history
```

### Estimate when complete
```bash
python3 ai_quota_monitor.py --estimate
```

### Manual dry-run (preview, no changes)
```bash
cd scraper && python3 ai_content_layer.py --dry-run --limit 5
```

### Manual run (1 category, 50 jobs)
```bash
cd scraper && python3 ai_content_layer.py --category SR_Result --limit 50
```

### Full run (use whole day's quota)
```bash
cd scraper && export GEMINI_API_KEY="your-key" && python3 ai_content_layer.py
```

### Regenerate site (without new AI)
```bash
cd site/jobs-web-main && python3 generate_all.py
```

---

## 📊 WHAT TO EXPECT (timeline)

| Day | API Calls | Total Processed | Status |
|---|---|---|---|
| Day 1 | ~1000 | 1000 | ✅ Running |
| Day 2 | ~1000 | 2000 | ✅ Running |
| Day 3 | ~1000 | 3000 | ✅ Running |
| Day 4 | ~1000 | 4000 | ✅ Running |
| Day 5 | ~1000 | 5000 | ✅ Running |
| Day 6 | ~432 | 5432 | ✅ **COMPLETE** |
| Day 7+ | ~0-50 (only new) | 5432+ | 🔄 Incremental |

---

## 🎯 DAILY CHECKLIST

- [ ] Morning: `python3 ai_quota_monitor.py` — quota theek?
- [ ] Afternoon: GitHub Actions log check (fail to nahi hua?)
- [ ] Weekend: `--history` check — average per day kya hai?
- [ ] Weekly: 3-5 random job pages khol — AI content dikhta hai?
- [ ] Monthly: Fact fields (title, dates, vacancy) unchanged hain check

---

## ⚠️ RED FLAGS

| Issue | Status | Action |
|---|---|---|
| Workflow running nahi | 🔴 STOP | Enable GitHub Actions (Settings → Actions) |
| GEMINI_API_KEY not set | 🔴 STOP | Add secret in Settings → Secrets → GEMINI_API_KEY |
| API requests stuck at 0 | 🟡 CHECK | Key valid? Workflow logs dekh |
| AI quality kharab | 🟡 MONITOR | Check facts pehle. Agar facts sahi: tune regenerate karo |
| Quota exhausted early | 🟢 NORMAL | Next day phir se shuru hoga, fallback content use hota hai |

---

## 📁 FILE LOCATIONS (remember)

```
repo-root/
├── scraper/
│   ├── ai_content_layer.py        ← NAYA AI layer
│   ├── scraper_all.py
│   └── scraper_merge.py
├── site/jobs-web-main/
│   └── generate_all.py            ← EDITED (AI hooks added)
├── .github/workflows/
│   └── daily_scraper_ai.yml       ← NAYA automated workflow
├── ai_quota_monitor.py            ← NAYA monitoring script
└── ai_daily_usage_history.json    ← AUTO-CREATED log
```

---

## 🔐 SECRETS (GitHub)

Settings → Secrets and variables → Actions:
```
GEMINI_API_KEY = "AIzaSy..."
```
(already set ✅)

---

## 📈 QUOTA MATH

```
Total jobs:     5432
Daily API limit: 1000
Days needed:    ceil(5432 / 1000) = 6 days

After day 6:
- All jobs have AI content ✅
- Only new/changed jobs use API (1-50/day typically)
- Cache hits save 90%+ of requests
```

---

## 🎛️ CONTROL POINTS (manual override)

| Situation | Command | Effect |
|---|---|---|
| Pause AI | `# comment out ai_content_layer.py in workflow` | Site regenerates, no new AI |
| Skip category | `--category SR_Result` limit | Only one category, others skip |
| Check 1 job | `--dry-run --limit 1` | Zero API calls, see prompt |
| Emergency revert | Delete ai_* fields from JSON | _backup_* content fallback |

---

## 📞 WHEN TO ESCALATE

- Workflow fails 3 days in a row → GitHub Actions status page check
- API gives 403 key error → Key validity check, re-add secret
- Site renders broken pages → Check log: generate_all.py error? data corrupt?

---

## ✅ SUCCESS SIGNALS

- ✅ Quota monitor shows increasing "Jobs with AI"
- ✅ GitHub Actions log shows "[AI CACHE HIT]" + "[AI CACHE MISS]" lines
- ✅ Sample job pages have "Overview", "Expert Analysis" sections
- ✅ Fact tables (vacancy, dates) still exact same numbers
- ✅ 6 days pass, estimate says "~0 days remaining" or "COMPLETE"

---

## 📚 Deep dive (if needed)

Full setup guide: `SETUP_GITHUB_ACTIONS_COMPLETE_GUIDE.md`
AI master prompt: `AI_CONTENT_LAYER_MASTER_PROMPT.md`
Deployment summary: `AI_LAYER_DEPLOY_SUMMARY.md`

---

**TL;DR:**
- Har din `python3 ai_quota_monitor.py` run karo
- 6 din me sab complete
- Cache baaki din zero overhead
- Facts kabhi nahi badlenge
- Enjoy unique content! 🚀
