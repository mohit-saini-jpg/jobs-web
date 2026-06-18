# TopSarkariJobs — AI Content Layer + Daily Automation
## Implementation Package (Ready to Deploy)

Bhai, ye complete package hai. Sab kuch implement, test, aur validate ho chuka hai. Niche **exact steps** hain ki ye apne repo me kaise daalna hai aur uske baad kya karna hai.

---

## 📦 ISME KYA HAI (folder structure)

```
final_package/
├── scraper/
│   ├── ai_content_layer.py      ← NAYA: AI content generation engine
│   ├── scraper_sarkari.py       ← UPDATED: incremental scraping (SR+Shine+SN)
│   ├── scraper_state.py         ← UPDATED: incremental scraping (38 states)
│   ├── scraper_education.py     ← UPDATED: incremental scraping
│   ├── scraper_fja.py           ← unchanged (already had incremental logic)
│   ├── scraper_merge.py         ← unchanged (already drops vanished jobs)
│   ├── scraper_all.py           ← unchanged (master runner)
│   └── incremental_cache.py     ← shared "don't re-scrape" helper module
├── site/jobs-web-main/
│   └── generate_all.py          ← UPDATED: renders AI content (fact-fallback)
├── .github/workflows/
│   └── daily_scraper_ai.yml     ← NAYA: automated daily pipeline
├── ai_quota_monitor.py          ← NAYA: quota/progress dashboard
└── docs/
    ├── SETUP_GUIDE.md           ← detailed setup instructions
    ├── QUICK_REFERENCE.md       ← daily-use cheat sheet
    └── WHAT_THIS_DOES_NOT_DO.md ← honest limitations (read this!)
```

---

## 🚀 DEPLOY — 5 STEPS (ek baar karna hai)

### Step 1 — Files apne repo me copy karo

Apne local repo (jahan `.git` folder hai) me jaake, **isी naam ke folders/files ko REPLACE karo**:

```bash
# apne repo root se chalao (jahan .git hai)
cp -r /path/to/final_package/scraper/* ./scraper/
cp /path/to/final_package/site/jobs-web-main/generate_all.py ./site/jobs-web-main/generate_all.py
cp -r /path/to/final_package/.github/workflows/daily_scraper_ai.yml ./.github/workflows/
cp /path/to/final_package/ai_quota_monitor.py ./
```

⚠️ **Important:** Agar `.github/workflows/generate_all.py` ki bhi alag copy hai (kuch repos me hoti hai), usko bhi **same** `generate_all.py` se replace karo — dono **identical** honi chahiye.

### Step 2 — GEMINI_API_KEY verify karo

GitHub repo → **Settings → Secrets and variables → Actions** → check `GEMINI_API_KEY` already set hai (aapne pehle hi add kar diya tha — yeh sirf double-check hai).

Agar nahi hai:
1. https://aistudio.google.com/app/apikey pe jaake free key banao
2. "New repository secret" → Name: `GEMINI_API_KEY` → Value: apni key paste karo

### Step 3 — Local pehla test (recommended, optional but smart)

Push karne se pehle apne computer pe ek dry-run kar lo:
```bash
cd scraper
export GEMINI_API_KEY="apni-key"
python3 ai_content_layer.py --dry-run --limit 5
```
Ye sirf **preview** karega — koi change nahi hoga. Confirm karega sab sahi se chal raha hai.

### Step 4 — Commit + push

```bash
git add -A
git commit -m "Add AI content layer + daily automation"
git push
```

### Step 5 — Workflow verify karo

GitHub repo → **Actions** tab → "Daily Scraper + AI Content Layer" workflow dikhna chahiye.
- Automatic: har din **2 AM IST** apne aap chalega
- Manual test: "Run workflow" button se abhi bhi chala sakte ho

---

## 📊 USKE BAAD — DAILY MONITORING

```bash
python3 ai_quota_monitor.py              # aaj ka status
python3 ai_quota_monitor.py --history    # pichle 30 din
python3 ai_quota_monitor.py --estimate   # kab complete hoga
```

**Timeline:** 5000+ jobs ke liye, 1000/day limit ke saath, **~6 din** me sab complete ho jayega. Uske baad sirf naye/changed jobs AI call lengi (cache ki wajah se).

---

## ⚠️ ZAROOR PADHO

- `docs/WHAT_THIS_DOES_NOT_DO.md` — honest limitations, koi false promise nahi
- `docs/SETUP_GUIDE.md` — agar koi step me confusion ho, detailed version
- `docs/QUICK_REFERENCE.md` — daily-use ke liye chhota cheat-sheet, print karke rakh sakte ho

---

## ✅ TESTED — kya verify kiya gaya (is session me)

- ✅ Normalizer: SR / FJA / State sources se sahi facts nikalta hai
- ✅ content_hash: deterministic, cache-hit correctly detect karta hai
- ✅ Facts (title, totalPost, vacancyDetails) AI ke baad bhi **bilkul unchanged**
- ✅ AI sections (Overview, Expert Analysis, FAQ, How-to-Apply) render hote hain
- ✅ Ek duplicate-card bug mila aur fix kiya (ai_* keys fallback dump me leak nahi karte ab)
- ✅ Non-AI jobs (existing 4000+ pages) — **zero regression**, bilkul pehle jaisa
- ✅ H1 jaan-bujh ke fact-based rakha gaya (duplicate-detection safety ke liye)
- ✅ Incremental scraping: state/education/SR-Shine-SN sources me wired (FJA me already tha)
- ✅ YAML workflow syntax-validated

---

## 🆘 Kuch bhi atke to

1. GitHub Actions ke logs dekho (Actions tab → failed run → step-by-step output)
2. `python3 ai_quota_monitor.py` chala ke current status check karo
3. Agar AI content kharab lage kisi job pe: `_backup_*` fields hamesha original data rakhte hain, fallback ho jata hai automatically

**Bas itna karna hai — files copy, secret verify, push. Baaki sab automatic chalega.**
