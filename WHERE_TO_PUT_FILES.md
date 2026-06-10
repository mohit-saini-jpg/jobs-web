# WHERE TO PUT FILES — State Job Links SEO Fix 2026-06-10

Repo: mohit-saini-jpg/jobs-web | Branch: main

Complete site ZIP. Extract karke poora content repo me replace karke push karo.
UI/design/layout/CSS kuch nahi badla.

## Is update me kya hua (aapki request)

### State page (/state/) ke job links ab SEO-friendly clean URL
Pehle: /state-job-detail.html?state=Bihar&slug=tmc-technician-... (query string,
non-SEO) YA external official link.

Ab: har job card ka link clean canonical page pe jaata hai:
  /jobs/tmc-technician-biomedical-scientific-assistant-2-posts/

Fix dono jagah:
- view.html  (main /state/ overview page) — buildCard + search dropdown ab
  job naam se clean slug bana ke /jobs/{slug}/ pe point karte hain.
- state-jobs.html (individual /state/{state}/ page) — internal clean /jobs/
  URL ko external link se PEHLE priority di.

96% (699/727) state jobs direct clean page pe match karte hain. Baaki ~28 ke
liye 301 redirect laga diya:
- 10 → unke actual /jobs/ page pe
- 16 → unke /state/{state}/ listing pe (jinka detail page nahi banta — no 404)

### Baaki sab same / intact
- Listing order (JSON order) same.
- Detail pages complete data ke saath same.
- Zero duplicate pages (one job = one URL) — pehle wala fix bana hua hai.
- Homepage single URL (/index.html → /) bana hua hai.

## Deploy ke baad
1. /state/ page kholo → kisi job card pe click → /jobs/{slug}/ clean URL khule.
2. GSC → Sitemaps → sitemap-index.xml refresh.
