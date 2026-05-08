# SEO Slug URL Migration — Deployment Guide

## What This Does

Converts all job detail URLs from:
```
https://www.topsarkarijobs.com/job.html?slug=bpssc-havildar-instructor-online-form-2026&k=wetupzv7n3kl
```
To clean SEO-friendly URLs:
```
https://www.topsarkarijobs.com/jobs/bpssc-havildar-instructor-online-form-2026/
```

---

## Files in This Package

| File | Purpose |
|---|---|
| `404.html` | GitHub Pages router — intercepts `/jobs/<slug>/` and hands off to template |
| `jobs/index.html` | Universal job detail template — reads slug from URL path |
| `script-patch.js` | Replacement `buildRedirectUrl()` for your `script.js` |
| `sitemap-jobs-generator.js` | Node.js script to generate `sitemap-jobs.xml` |
| `sitemap-jobs.xml` | Sample sitemap (regenerate with the generator script) |

---

## Step 1 — Add 404.html to Your Repository Root

Copy `404.html` to the **root** of your GitHub Pages repository.

> GitHub Pages automatically serves `404.html` for any URL that doesn't match a real file. The routing script inside it detects `/jobs/<slug>/` paths and redirects to `/jobs/index.html`.

---

## Step 2 — Add the jobs/ Template

Copy the `jobs/` folder (containing `index.html`) to your **repository root**.

Your repo structure should look like:
```
/
├── 404.html          ← new
├── index.html
├── job.html          ← keep (old URLs still work during transition)
├── jobs/
│   └── index.html    ← new
├── script.js
├── styles.css
├── dynamic-sections.json
└── ...
```

---

## Step 3 — Patch script.js

Open `script.js` and find the `buildRedirectUrl` function (around **line 88**):

```js
// OLD — generates ?slug=...&k=... URLs
function buildRedirectUrl(targetUrl, label = "", sectionId = "") {
  const qs = new URLSearchParams();
  qs.set("slug", slugifyTitle(label || targetUrl));
  qs.set("k", urlRedirectFingerprint(to));
  ...
  return `job.html?${qs.toString()}`;
}
```

Replace it with:

```js
// NEW — generates /jobs/<slug>/ clean URLs
function buildRedirectUrl(targetUrl, label = "", sectionId = "") {
  const slug = slugifyTitle(label || targetUrl);
  if (!slug || slug === "official-link") return "#";
  return "/jobs/" + slug + "/";
}
```

That's the **only change** needed in `script.js`.

---

## Step 4 — Generate the Sitemap

Run the generator locally (requires Node.js):

```bash
node sitemap-jobs-generator.js
```

This reads `dynamic-sections.json` and outputs `sitemap-jobs.xml` with one `<url>` per job.

Then reference it in your main `sitemap.xml`:

```xml
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://www.topsarkarijobs.com/sitemap.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://www.topsarkarijobs.com/sitemap-jobs.xml</loc>  <!-- ADD THIS -->
  </sitemap>
</sitemapindex>
```

---

## Step 5 — Backwards Compatibility (keep old URLs working)

The old `job.html?slug=...&k=...` URLs **still work** because `job.html` is still in your repo. No redirects needed during transition. Once Google has re-crawled all pages with the new URLs, you can optionally add a redirect in `job.html`:

```html
<script>
  // In job.html, add at the top of the init script:
  var params = new URLSearchParams(location.search);
  var slug = params.get('slug');
  if (slug) {
    window.location.replace('/jobs/' + slug + '/');
  }
</script>
```

---

## How the Routing Works (Technical)

```
Browser requests: /jobs/bpssc-havildar-instructor-online-form-2026/
        │
        ▼
GitHub Pages: no file at that path → serves 404.html
        │
        ▼
404.html JS: detects /jobs/<slug>/ pattern
  → saves slug to sessionStorage('__tsj_slug')
  → window.location.replace('/jobs/index.html')
        │
        ▼
/jobs/index.html loads
  → reads slug from sessionStorage
  → calls history.replaceState(null,'','/jobs/bpssc-havildar.../') 
    (restores pretty URL in browser bar)
  → fetches dynamic-sections.json
  → matches slug → renders job page
  → injects canonical, OG, JobPosting schema, breadcrumb schema
```

---

## SEO Features in jobs/index.html

| Feature | Implementation |
|---|---|
| Dynamic `<title>` | Set from job name + site name |
| Dynamic `<meta description>` | Job name + eligibility summary |
| Dynamic `<link rel="canonical">` | Set to `/jobs/<slug>/` (no params) |
| Open Graph tags | og:title, og:description, og:url, og:image |
| Twitter Card | summary_large_image |
| JobPosting schema | title, org, lastDate, vacancies, location |
| BreadcrumbList schema | Home → Jobs → Job Name |
| No tracking params in URL | Clean `/jobs/<slug>/` only |

---

## After Deployment

1. Submit `sitemap-jobs.xml` to Google Search Console
2. Use the URL Inspection tool to test a `/jobs/<slug>/` URL
3. Check that canonical shows `/jobs/<slug>/` not `job.html?...`
4. Monitor crawl coverage over 2–4 weeks

---

## Notes

- The `k` (fingerprint) parameter is **not needed** for the new URL system — the slug alone is used to match jobs in `dynamic-sections.json`.
- The matching uses a token-based fuzzy match (55% threshold) identical to the existing `matchBySlug` logic in `job.html`.
- GitHub Pages does not support server-side redirects or `.htaccess`, so the 404.html trick is the standard solution.
