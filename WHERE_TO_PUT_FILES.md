# 📁 FAQ FIX + AUTO-FAQ SYSTEM (2026-06-10)

FULL SITE rebuild. Do 2 cheezein theek/add ki:

## ✅ 1) FAQ answer-not-showing BUG — FIXED
Problem: details page pe FAQ ka sirf Question dikhta tha, Answer nahi (collapsed/hidden).
Asli wajah: `styles-detail.css` me `.faq-a{display:none}` tha, par accordion toggle wali
`faq-init.js` detail pages pe load hi nahi ho rahi thi — to answer hamesha chhupa rehta tha.

Fix (3 cheezein):
- `faq-init.js` ab har detail page pe load hoti hai (accordion: question pe click → answer khulta hai)
- CSS ab "progressive enhancement" — answer **default visible** hai; JS load hoke accordion banata hai.
  Agar JS fail ho to bhi answer dikhta rahega (kabhi chhupega nahi). SEO + user dono ke liye behtar.
- Pehla FAQ default open + chevron icon (▼) add kiya.
- JSON me duplicate FAQ (Q1. prefix wale + bina prefix) the — wo de-dup hoke clean 10 ho jaate hain.

## ✅ 2) AUTO-FAQ Generation System (SEO) — ADDED
Jin pages pe JSON me FAQ nahi hai, wahan ab **page ke ASLI data se** 5-10 FAQ apne aap ban jaate hain
(last date, vacancies, qualification, age, fee, selection, salary, org, website, apply mode).
- Sirf jo field maujood hai usi se FAQ banta hai — **kabhi fake/galat data nahi** (spec ka rule).
- Category-aware: Result / Admit Card / Answer Key / Admission / Date Sheet pages ko unke hisaab se relevant FAQ milte hain.
- Matching FAQPage JSON-LD schema bhi banta hai (visible FAQ = schema FAQ, 100% match — verified).
- Jahan JSON me FAQ pehle se hai, wahan wahi use hote hain (auto-FAQ nahi banta, duplicate nahi).

**Coverage: 91% job pages pe ab FAQ hai (pehle bahut kam tha).** Baaki ~9% (govt scheme/info pages
jaise ₹3000 Pension Yojana, Aadhaar forms) me koi structured data nahi — unme fake FAQ banane ki bajaye
(spec ke "never invent" rule ke mutabik) FAQ skip kiya. Ye sahi behavior hai.

## 📂 Files kahan rakhni hain (poora folder deploy karo)
| File | Kahan |
|------|-------|
| Saari `jobs/*/`, `section/*/`, etc. pages | yathaasthaan |
| `generate_all.py` (+ `.github/workflows/` copy) | Root |
| `styles-detail.css` (+ workflow copy) | Root — ISME FAQ visible-by-default CSS hai, zaroor replace karo |
| `faq-init.js` (+ workflow copy) | Root — accordion toggle, zaroor replace karo |

## ⚠️ Note
- `styles-detail.css` aur `faq-init.js` dono zaroor replace karo — inke bina FAQ answer phir se chhup sakta hai.
- Sab fix generator + assets me permanent hai → future workflow runs pe automatically rahega.
- Pichhle saare fixes intact: 0 duplicate canonical, rich share, social links, state cards.

## 🚀 Deploy ke baad
1. Koi bhi detail page (jaise KSP Police) kholo → FAQ me Question + Answer dono dikhne chahiye.
2. Question pe click karo → accordion toggle (answer khule/band ho).
3. Jis page pe JSON FAQ nahi tha (jaise koi recruitment) → auto-generated FAQ + schema dikhega.
