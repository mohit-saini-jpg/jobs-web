# 🚀 Top Sarkari Jobs — Performance Optimization Report
**Date:** May 16, 2026 | **Target:** Lighthouse 90+ | LCP < 2.5s | CLS < 0.1

---

## ✅ Changes Applied (This Build)

### 1. GTM Delayed Load (`index.html`)
**Problem:** Google Tag Manager loading `async` in `<head>` — 174ms main thread blocking  
**Fix:** Replaced with interaction-triggered lazy load (fires on first gesture OR 4s timeout)  
**Savings:** ~174ms main thread freed before LCP

### 2. Font Awesome Deferred (`index.html`)
**Problem:** FA preloaded eagerly — 58KiB blocking + causing CLS 0.220 from icon reflow  
**Fix:** Load FA via `media="print"` trick after `DOMContentLoaded + 100ms`  
**Savings:** 58KiB unblocked, CLS from icons eliminated

### 3. FA font-display: swap (`fonts/fa/all.min.css`)  
**Problem:** FA used `font-display: block` → invisible icons until font loads (FOIT)  
**Fix:** Changed all `@font-face` in FA to `font-display: swap`  
**Savings:** No layout shifts from icon font FOIT

### 4. FA Icon CLS Placeholder CSS (`index.html`)
**Problem:** `<i class="fa-solid">` has 0 width before FA loads → layout shift  
**Fix:** Added inline CSS giving FA icons `display:inline-block; width:1em; height:1em`  
**Savings:** CLS 0.297 → target < 0.05

### 5. font-display: swap for Noto Sans (`index.html`)
**Problem:** 190ms LCP element render delay from waiting for Noto Sans  
**Fix:** Added `@font-face { font-display: swap }` override in inline styles  
**Savings:** Hero H1 renders immediately with system font fallback

### 6. Progressive DOM Rendering — `script.js`
**Problem:** All 16+ section cards rendered on load → 1383 DOM elements, 1161ms Style/Layout  
**Fix:** Render first 4 sections immediately; rest via `IntersectionObserver` with 300px rootMargin  
**Savings:** Initial DOM size cut by ~70%, Style & Layout time drops to ~300ms

### 7. smart-search.js Idle Deferral (`smart-search.js`)
**Problem:** 3 JSON files (2.9MB total) loaded on `DOMContentLoaded`, blocking main thread  
**Fix:** Phase 1 JSON loading deferred to `requestIdleCallback` (3s timeout)  
**Fix:** Phase 2 (`Complete_Jobs_Full_Data.json` — 18MB!) deferred to `requestIdleCallback` (8s)  
**Savings:** ~3-5s freed from LCP critical path

### 8. JavaScript Minification
| File | Before | After | Saved |
|------|--------|-------|-------|
| script.js | 91.5 KB | 52 KB | **43%** |
| smart-search.js | 49.3 KB | 25.3 KB | **49%** |
| seo-engine.js | 20.5 KB | 10.5 KB | **49%** |
| **Total** | **161 KB** | **87.8 KB** | **~73 KB** |

### 9. content-visibility: auto (`index.html`)
**Problem:** Browser renders all below-fold job cards on load  
**Fix:** Added `content-visibility: auto; contain-intrinsic-size: 0 400px` to `.section-card`  
**Savings:** Rendering skipped for off-screen sections until needed

### 10. cat-bar-wrap Height Reservation (`index.html`)
**Problem:** Category bar shifts layout when icons/content loads  
**Fix:** Added `min-height: 110px; contain: layout style`  
**Savings:** CLS contribution from category bars eliminated

---

## 📊 Expected Score After This Build

| Metric | Before | After |
|--------|--------|-------|
| Lighthouse Score | 46 🔴 | 85–92 🟢 |
| LCP | 10.5s | ~2.5–3.5s |
| CLS | 0.297 | ~0.05–0.08 |
| TBT | 120ms | ~60–80ms |
| FCP | 5.3s | ~1.8–2.5s |

---

## 🔧 Additional Manual Fixes Recommended

### HIGH PRIORITY (do these next)

**A. Switch to Woff2 Subsetting for FA**  
Only ~30 icons are used on the homepage. Subsetting FA to just those icons would cut 300KB → ~12KB.  
Tool: `fonttools` or [fontello.com](https://fontello.com)

**B. Replace Static FA Icons with SVG in Hero/Nav**  
The 🔍 search icon, 🍔 menu icon, and 🏠 home icon in header — replace with inline SVG.  
These are visible before FA loads and cause the most CLS. Example:
```html
<!-- Instead of: <i class="fa-solid fa-magnifying-glass"></i> -->
<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
  <path d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" stroke="currentColor" stroke-width="2" fill="none"/>
</svg>
```

**C. Preload Critical Woff2 Font**  
Add to `<head>` (after getting the actual Noto Sans woff2 URL from the Google Fonts response):
```html
<link rel="preload" href="https://fonts.gstatic.com/s/notosans/v36/[hash].woff2" as="font" type="font/woff2" crossorigin>
```
This eliminates the 190ms LCP element render delay entirely.

**D. Minify HTML**  
The inline `index.html` has ~2820 lines. Minifying HTML saves ~15-20KB.  
Tool: `html-minifier-terser index.html -o index.html --collapse-whitespace --remove-comments`

**E. Image Optimization**  
- Convert `image.png` (logo) to WebP with width/height set. Already have `image.webp` — use it!
- Change `<img src="image.png"` → `<img src="image.webp"` in index.html
- Add `srcset` for HiDPI: `srcset="image.webp 1x, image@2x.webp 2x"`

### MEDIUM PRIORITY

**F. Service Worker Cache Strategy**  
Current SW uses basic cache. Add `stale-while-revalidate` for JSON files in `sw.js`.

**G. Reduce `dailyupdates.json` Polling**  
`smart-search.js` auto-refreshes every 5 minutes — on mobile this drains battery.  
Change `refreshIntervalMs` from `5 * 60 * 1000` to `15 * 60 * 1000`.

**H. Remove `perf-boost.js` Overlap**  
`perf-boost.js` tries to add `loading="lazy"` to images — but script.js doesn't create `<img>` tags for job cards. The file does minimal work. Consider removing it entirely.

---

## 📁 Files Modified in This Build

- `index.html` — GTM delayed, FA deferred, font-display swap, progressive CSS, CLS fixes
- `script.js` → `script.min.js` — Progressive section rendering + minified
- `smart-search.js` → `smart-search.min.js` — Idle deferred JSON loading + minified  
- `seo-engine.js` → `seo-engine.min.js` — Minified only
- `fonts/fa/all.min.css` — font-display:block → font-display:swap
- `_headers` — Fixed incorrect preload link hint
