# TSJ Homepage SEO & Duplicate-URL Fix — DONE

Saare 4 tasks complete. Files `seo_fix/` me hain, repo structure preserve karke.

## ✅ Task 1 — Duplicate homepage / legacy URL competition

**18 legacy `.html` files ko redirect-stub bana diya** (har ek apne canonical pe
JS-redirect + canonical tag). Stubs `legacy_stubs/` me:
view, about, privacy, result, terms, contact, state-jobs, education-jobs,
admit-card, jobs-index, search, tools-audio-video, tools, result-section,
admit-card-section, tools-image, tools-pdf, tools/about.html

**`index.html` ko NHI chhua** — GitHub Pages pe `/` aur `/index.html` SAME file
hai. Stub karne se homepage hi mar jaata. Uska `<link canonical="/">` already
`/index.html` duplicate signal handle karta hai. (Spec me ye edge-case miss tha —
maine deliberately skip kiya.)

**Internal links fixed** (sab clean URL pe point karte hain, stub pe nahi):
- `scripts/generate_pages.py` + workflow `generate_jobs_root.py`: author URL
  `/about.html` → `/about/`
- `sitemap-auto.js`: nav links (search/about/contact/privacy/terms) → clean URLs
- tools section + `tools/about.html`: legacy links → absolute clean URLs

**No `noindex` on stubs** (per spec — canonical tag alone is the correct signal).
**Files NOT deleted** — stubbed, so link-equity passes through.

## ✅ Task 2 — Homepage title/meta stabilized

**Root cause mila:** `seo-engine.min.js` homepage detect karke load ke baad
`document.title` ko JS se OVERRIDE kar raha tha → Google ko different title dikhta
tha (raw HTML vs JS-rendered) → Google ne title pe trust khoya.

**Fix:** Dono `seo-engine.js` + `seo-engine.min.js` me home-page title/desc override
**disable** kiya. Ab homepage ka title 100% static HTML se aata hai, JS kuch override
nahi karta. WebPage schema ab `document.title` use karta hai.

**Finalized (sab jagah consistent — title, og:title, twitter:title):**
- Title: `Top Sarkari Jobs 2026 – Latest Govt Jobs, Results & Admit Cards` (62 chars)
- Desc (139 chars): `Latest government job notifications, admit cards, results & answer keys for SSC, Railway, Banking, Police, UPSC & State PSC. Updated daily.`

## ✅ Task 3 — Duplicate/conflicting WebSite JSON-LD fixed

- 2 WebSite nodes the → ab **sirf 1** (the one inside `@graph`, jismein sahi
  `publisher.@id = #organization`)
- Duplicate "ISSUE-028" standalone block (jisme broken `#org` reference tha)
  **delete kar diya**
- `alternateName` ko `["TSJ"]` tak trim kiya (generic "Sarkari Naukri" claims hata
  diye — spec recommendation)
- **Validated:** dono ld+json blocks valid JSON, har `@id` reference resolve hota
  hai (0 unresolved, 0 broken `#org`)

## ✅ Task 4 — Sitemap cleanup + verification

- Saare legacy `.html` paths sitemaps se removed (sitemap-pages/admitcards/results)
- `build_sitemaps.py` me hard `.html` exclusion + `sitemap-pages.xml`
  always-regenerate (taaki dobara stale na ho). Workflow copy bhi synced.

**Verification checklist — ALL PASS:**
- [x] 18 legacy files = redirect stubs (view source = sirf stub)
- [x] index.html intact (3458 lines, not a stub)
- [x] Exactly 1 WebSite node; har @id resolve hota hai
- [x] 0 broken `#org` refs
- [x] Homepage title = finalized version
- [x] 0 `.html` legacy paths in sitemaps
- [x] og/twitter title+desc = main title+desc (no drift)
- [x] JS homepage title override disabled (both .js + .min.js)

---

## 📋 MOHIT KO MANUALLY KARNA HAI (code nahi)

1. **Search Console → Removals → "Remove outdated content"**: har legacy URL submit
   karo: `/index.html`, `/view.html`, `/about.html`, `/privacy.html`,
   `/result.html`, `/terms.html`, `/tools-audio-video.html`, baaki sab stubbed.
2. **Search Console → URL Inspection on `/`** → "Google-selected canonical" check
   karo. Abhi `/` ke alawa kuch dikhe to wo confirm karta hai duplication abhi live
   hai — 1-2 recrawl me resolve ho jayega.
3. **Sitemap resubmit** karo Search Console me.
4. **Title 4-6 hafte mat badalna** — bar-bar edit karne se hi Google ne trust khoya
   tha. Ab stable rehne do.
5. **Schema validate** karo: Google Rich Results Test pe `/` daalo — WebSite +
   Organization nodes pe 0 errors aane chahiye.

## Deploy
`seo_fix/` ke files ko repo me same path pe replace karo:
- `index.html` → root
- `seo-engine.js`, `seo-engine.min.js`, `sitemap-auto.js` → root
- `legacy_stubs/*.html` → root (tools_about.html → `tools/about.html`)
- `scripts/build_sitemaps.py` + `.github_workflows/build_sitemaps.py` (dono same)
- `scripts/generate_pages.py` + `.github_workflows/generate_jobs_root.py`
- `sitemap*.xml` → root
Push → hard refresh → sitemap resubmit.
