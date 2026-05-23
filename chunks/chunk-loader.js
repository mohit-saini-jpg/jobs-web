/**
 * TopSarkariJobs – Chunked JSON Loader
 * =====================================
 * Drop-in replacement for fetching large monolithic JSON files.
 * Loads only the chunk needed for the current page/view.
 *
 * Usage:
 *   const jobs = await ChunkLoader.getMergedCategory('LATEST_JOBS_NEW');
 *   const stateJobs = await ChunkLoader.getState('haryana');
 *   const stateListing = await ChunkLoader.getStateIndex(); // ~light index
 *
 * CDN Cache: Each chunk has a stable URL → aggressive CDN caching.
 */

const ChunkLoader = (() => {
  const BASE = '/chunks';
  const cache = new Map();

  async function fetchJSON(url) {
    if (cache.has(url)) return cache.get(url);
    const r = await fetch(url);
    if (!r.ok) throw new Error(`ChunkLoader: ${r.status} ${url}`);
    const data = await r.json();
    cache.set(url, data);
    return data;
  }

  // ── merged_sarkari_data.json replacements ──────────────────────────────

  /** Listing-only (lightweight) — all jobs, minimal fields */
  async function getMergedListing() {
    return fetchJSON(`${BASE}/merged/listing.json`);
  }

  /** Full category shard: listing for a specific category */
  async function getMergedCategory(category) {
    const slug = category.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    return fetchJSON(`${BASE}/merged/category/${slug}.json`);
  }

  /** Paginated global listing page */
  async function getMergedPage(page = 1) {
    return fetchJSON(`${BASE}/merged/pages/page-${page}.json`);
  }

  /** Full detail for one job (lazy-loaded on job page) */
  async function getMergedDetail(slug) {
    return fetchJSON(`${BASE}/merged/detail/${slug}.json`);
  }

  /** Manifest — what chunks exist */
  async function getMergedManifest() {
    return fetchJSON(`${BASE}/merged/manifest.json`);
  }

  // ── state-jobs-data.json replacements ─────────────────────────────────

  /** Light state index — all states, listing fields only */
  async function getStateIndex() {
    return fetchJSON(`${BASE}/state/index.json`);
  }

  /** One state's listing data */
  async function getState(stateId) {
    return fetchJSON(`${BASE}/state/${stateId}.json`);
  }

  /** Full detail for one state job (lazy-loaded) */
  async function getStateDetail(stateId, slug) {
    return fetchJSON(`${BASE}/state/detail/${stateId}/${slug}.json`);
  }

  return {
    getMergedListing,
    getMergedCategory,
    getMergedPage,
    getMergedDetail,
    getMergedManifest,
    getStateIndex,
    getState,
    getStateDetail,
  };
})();

// ── Backwards-compatible shims ─────────────────────────────────────────────
// These replace the old global fetch('merged_sarkari_data.json') pattern.

/**
 * Drop-in: replaces fetch('/merged_sarkari_data.json').then(r=>r.json())
 * Returns same {scraped_at, total, jobs} shape but 92% smaller payload.
 */
window.__getJobsListingData = () => ChunkLoader.getMergedListing();

/**
 * Drop-in: replaces fetch('/state-jobs-data.json').then(r=>r.json())
 * Returns {sections:[...]} with listing-only items (no heavy detail).
 * For detail, use ChunkLoader.getStateDetail(stateId, slug).
 */
window.__getStateJobsData = () => ChunkLoader.getStateIndex();

// Export for ES module environments
if (typeof module !== 'undefined') module.exports = ChunkLoader;
