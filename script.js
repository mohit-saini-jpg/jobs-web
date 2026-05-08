/**
 * PATCH for script.js — SEO Slug URL Migration
 * =============================================
 * Replace the existing buildRedirectUrl() function (around line 88)
 * with this version. Everything else in script.js stays the same.
 *
 * BEFORE (old — generates query-param URLs):
 *   job.html?slug=bpssc-havildar-instructor-online-form-2026&k=wetupzv7n3kl
 *
 * AFTER (new — generates clean slug URLs):
 *   /jobs/bpssc-havildar-instructor-online-form-2026/
 *
 * The `k` fingerprint and `section` params are dropped entirely.
 * The /jobs/<slug>/index.html template resolves the job by matching
 * the slug against dynamic-sections.json directly.
 */

// ─── REPLACE THIS FUNCTION IN script.js (around line 88) ───────────────────

function buildRedirectUrl(targetUrl, label = "", sectionId = "") {
  // Generate the slug from the label (same slugifyTitle logic already in script.js)
  const slug = slugifyTitle(label || targetUrl);
  if (!slug || slug === "official-link") return "#";

  // Clean SEO URL — no query params, no tracking key
  return "/jobs/" + slug + "/";
}

// ───────────────────────────────────────────────────────────────────────────
// NOTE: The openInternal() function (line 83) that generates view.html?url=…
// is NOT changed — those links go to view.html, not job pages.
//
// The isRedirectGatedLink() guard already prevents double-wrapping, so
// only section-link clicks from index.html and view.html list items
// will produce the new /jobs/<slug>/ URLs.
// ───────────────────────────────────────────────────────────────────────────
