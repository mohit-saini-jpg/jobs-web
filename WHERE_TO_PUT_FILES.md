# 📁 IMPORTANT LINKS — ROW LAYOUT (Name + Open button) 2026-06-10

FULL SITE rebuild. Saare detail pages ke link section ka layout Image jaisa kar diya.

## ✅ Kya change hua

Important Links / Useful Links section ab **row layout** me hai (jaisa aapne Image me dikhaya):
- **Left side:** link ka naam/label (jaise "Apply Online", "Official Website", "Download Notification")
- **Right side:** colored **"Open"** button with icon

Har link type ka apna rang (Image jaisa):
- Apply Online → green
- Official Website → blue
- Download Notification / PDF → red
- Admit Card → teal
- Answer Key / Result → yellow
- Register → orange
- Login → purple

Ye layout site ke **saare 2,600+ detail pages** pe lag gaya — chahe link `important_links`, `useful_links` (SarkariResult), `all_links`, ya tables se aaye. Sab jagah same consistent "Name + Open" row design.

## 📂 Files kahan rakhni hain (poora folder deploy karo)
| File | Kahan |
|------|-------|
| Saari `jobs/*/`, `section/*/`, etc. pages | yathaasthaan |
| `generate_all.py` (+ `.github/workflows/` copy) | Root |
| `styles-detail.css` (+ workflow copy) | Root — ISME naya .lk-row / .lk-open CSS hai, zaroor replace karo |
| `faq-init.js` (+ workflow copy) | Root |

## ⚠️ Note
- `styles-detail.css` zaroor replace karo — naye link row layout ka CSS isi me hai. Iske bina links tute dikhenge.
- Baaki design/UI same — sirf link section ka layout Image jaisa hua.
- Fix generator me permanent hai → future workflow runs pe automatically rahega.
- Blocked domains (sarkariresult/freejobalert/etc.) ab bhi skip hote hain.
- Verified: 2,604 pages new row layout, 0 duplicate canonical, 3,200 job pages, FAQ 91%, JS valid.

## 🚀 Deploy ke baad
Koi bhi detail page kholo → "Important Links" / "Useful Links" section me har link ek row me dikhna chahiye:
left me naam, right me colored "Open" button (bilkul Image jaisa).
