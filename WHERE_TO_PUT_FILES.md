# 📁 DETAIL PAGE SPEC — PERMANENT FIXES (2026-06-10)

FULL SITE rebuild. Aapke detail-page generation spec ke saare gaps generator me permanently fix kiye.

## ✅ Kya-kya fix hua (spec ke against)

1. **JobPosting schema complete** — ab in fields ke saath:
   - `applicationDeadline` (last date)
   - `totalJobOpenings` (numeric vacancies, e.g. 3991)
   - `speakable` (voice-search SEO: .detail-h1, .notice, .stats-bar)
   - (pehle se: datePosted, validThrough, baseSalary, hiringOrganization, jobLocation, etc.)

2. **TSJ window variables** — har detail page me ab ye set hote hain (page fully pre-rendered, JS renderer band):
   - `__TSJ_SLUG`, `__TSJ_CANONICAL`, `__TSJ_STATIC_PAGE`
   - `__TSJ_PSR_DISABLED = true`, `__TSJ_RENDERER_DISABLED = true`
   - URL normalize (replaceState to /jobs/{slug}/)

3. **FAQ Q/A swap fix** — agar JSON me question/answer ulte ho (answer me sawaal, question me jawab) to apne aap swap ho jaate hain.

4. **Qualification section proper** — ab dedicated render:
   - KV table: education_qualification, qualification, eligibility, required_degree, technical_qualification, experience_required, details, nationality
   - `matched_qualifications` array → badges ke roop me ("Matched Qualifications")

5. **Pehle se sahi (verified)**: blocked domains (sarkariresult/freejobalert/etc.), structured_links render-last, useful_links _all skip, text_sections/tables merge, FAQ accordion + chevron + first-open, auto-FAQ system.

## 📂 Files kahan rakhni hain (poora folder deploy karo)
| File | Kahan |
|------|-------|
| Saari `jobs/*/`, `section/*/`, etc. pages | yathaasthaan |
| `generate_all.py` (+ `.github/workflows/` copy) | Root |
| `styles-detail.css`, `faq-init.js` (+ workflow copies) | Root |

## ⚠️ Note
- Design/UI/layout bilkul same — sirf schema, window-vars, qualification rendering aur FAQ logic improve hua.
- Sab fix generator me permanent hai → future workflow runs pe automatically rahega.
- Verified: JobPosting/BreadcrumbList/FAQPage teeno JSON-LD valid, 0 duplicate canonical, 3,200 job pages, FAQ 91% coverage, JS valid.

## 🚀 Deploy ke baad
1. Koi job page ka source dekho → `__TSJ_PSR_DISABLED` + JobPosting me `totalJobOpenings`/`applicationDeadline`/`speakable` hone chahiye.
2. Qualification section me agar matched_qualifications hai to badges dikhne chahiye.
