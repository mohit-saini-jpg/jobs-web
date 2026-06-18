# TopSarkariJobs — Complete Site + AI Content Layer

Bhai, ye **complete, ready-to-push package** hai — puri website (sab HTML pages, JSON data, assets) **+ AI content layer fully implemented**, dono saath me.

---

## 📦 ISME KYA HAI

Ye **poora repo hai as-is**, sirf 4 cheezein add/update ki gayi hain:

| File/Folder | Status | Kya hai |
|---|---|---|
| `generate_all.py` (root) | **UPDATED** | AI render hooks added (title/meta/overview/FAQ override, fact-fallback) |
| `.github/workflows/generate_all.py` | **UPDATED** | Same file, md5-identical (verified) |
| `scraper/` | **NAYA folder** | Saare scrapers + naya `ai_content_layer.py` |
| `.github/workflows/daily_scraper_ai.yml` | **NAYA** | Automated daily scrape+AI workflow |
| `ai_quota_monitor.py` (root) | **NAYA** | Quota/progress dashboard script |
| `docs/` | **NAYA folder** | Setup guide, cheat-sheet, honest limitations |
| `README.md` | **NAYA** | Ye file |

**Baaki SAB** (5000+ HTML pages, CSS, JS, images, sab existing workflows) — **bilkul waisa hi hai jaisa tha**, kuch nahi chhua gaya.

---

## 🔄 PIPELINE — Kaise kaam karta hai (deeply verified)

Aapke repo me already ek daily workflow hai — `auto-update-jobs.yml`, jo daily **7 AM IST** pe `generate_all.py` chalata hai, sitemap banata hai, push karta hai. Maine **deeply verify kiya** (actual file padhke, guess nahi) ki ye exactly aisa karta hai.

Isliye naya AI workflow **generate_all.py dobara NAHI chalata** — sirf data + AI tak limited hai:

```
2:00 AM IST  →  daily_scraper_ai.yml (NAYA)
                scrape (naya data) → merge → AI content fill → JSON commit
                                                                    │
                                                                    ▼
7:00 AM IST  →  auto-update-jobs.yml (PEHLE SE EXISTING, untouched)
                wahi JSON padhta hai → generate_all.py (AI hooks ke saath)
                chalata hai → sitemap → push → live site
```

**Iska fayda:** sirf EK jagah se generate+push hoti hai — **zero conflict risk**, purana stable workflow waisa hi chalta hai jaisa chal rahas tha.

---

## 🚀 DEPLOY — kya karna hai

Ye **already extract karne layak ek complete repo hai**. Bas:

### Step 1 — Apne local repo me ye replace karo
```bash
# apne existing local clone me jaake, ye sab is ZIP se copy karo:
- generate_all.py                          (root)
- .github/workflows/generate_all.py
- .github/workflows/daily_scraper_ai.yml   (nayi file)
- scraper/                                  (poora naya folder)
- ai_quota_monitor.py                       (root)
- docs/                                     (naya folder)
```

(Ya seedha pura ye ZIP extract karke push kar do agar yehi aapka pura repo represent karta hai — but safer hai ki sirf upar wali files apne existing clone me merge karo, taaki kisi aur uncommitted local change ka loss na ho.)

### Step 2 — GEMINI_API_KEY verify karo
Settings → Secrets and variables → Actions → `GEMINI_API_KEY` already set hai ✅ (aap confirm kar chuke ho).

### Step 3 — Push
```bash
git add -A
git commit -m "Add AI content layer + daily automation"
git push
```

### Step 4 — Verify
GitHub → Actions tab → "Daily Scraper + AI Content Layer" workflow dikhna chahiye, saath me purana "🔄 Auto Update Jobs + Sitemap + Cache Bust" bhi.

---

## 📊 Uske baad — daily monitoring

```bash
python3 ai_quota_monitor.py              # aaj ka status
python3 ai_quota_monitor.py --history    # pichle 30 din
python3 ai_quota_monitor.py --estimate   # kab complete hoga
```

**Timeline:** 5000+ jobs, 1000/day limit → **~6 din** me sab complete. Uske baad sirf naye/changed jobs AI call lengi.

---

## ✅ TESTED (is session me verify kiya)

- ✅ Normalizer: 4 source shapes (SR/FJA/State/Education) se sahi facts
- ✅ content_hash caching: deterministic, cache-hit confirmed
- ✅ Facts (title, totalPost, vacancyDetails) AI ke baad **bilkul unchanged**
- ✅ AI sections (Overview, Expert Analysis, FAQ, How-to-Apply) render hote hain
- ✅ Duplicate-card bug pakda + fix kiya
- ✅ Non-AI jobs — zero regression
- ✅ H1 jaan-bujh ke fact-based (dedup safety)
- ✅ Real local test (aapne khud kiya): 4/5 jobs successfully AI content generate hua
- ✅ Workflow paths real repo structure (`jobs-web-main` = root) ke against verify kiye, mismatch fix kiya

---

## ⚠️ ZAROOR PADHO

`docs/WHAT_THIS_DOES_NOT_DO.md` — koi false promise nahi. Ye system content unique banata hai, lekin Google ranking/indexing/trust guarantee **NAHI** deta — wo Google ke algorithm pe depend karta hai.

---

## 🆘 Kuch atke to

1. GitHub Actions logs check karo (Actions tab → failed run)
2. `python3 ai_quota_monitor.py` chala ke status dekho
3. `_backup_*` fields hamesha original data rakhte hain — AI fail ho to automatic fallback
