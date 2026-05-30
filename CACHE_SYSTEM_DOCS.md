# Zero-Stale Cache Engine v8.0 — Implementation Guide
## Top Sarkari Jobs | topsarkarijobs.com

---

## 1. How the 3-Layer Cache System Works

```
Request comes in
      │
      ▼
┌─────────────────────────────────────────────┐
│  LAYER 1: Service Worker (sw.js)            │
│  Cache names: tsj-static-{VER}             │
│               tsj-pages-{VER}              │
│               tsj-data-{VER}               │
│               tsj-offline-{VER}            │
│                                             │
│  Strategy per resource:                     │
│  • HTML pages       → Network First         │
│  • dailyupdates.json → Network First (fresh)│
│  • sections-index.json → SWR 10-min TTL    │
│  • /data/*.json     → SWR 30-min TTL        │
│  • other *.json     → SWR 15-min TTL        │
│  • versioned JS/CSS → Cache First           │
│  • unversioned JS   → Network First         │
│  • version.json     → Always Network        │
└─────────────────────────────────────────────┘
      │ if SW misses / offline
      ▼
┌─────────────────────────────────────────────┐
│  LAYER 2: sessionStorage (JS-side cache)    │
│  Keys:                                      │
│  __sr_merged_v11   → Complete_Jobs (15min)  │
│  __ticker_sec_v2   → sections-index (15min) │
│  TTL managed by inline scripts              │
│  Cleared on: new deploy detection,          │
│              schema version bump            │
└─────────────────────────────────────────────┘
      │ if sessionStorage empty
      ▼
┌─────────────────────────────────────────────┐
│  LAYER 3: Network                           │
│  Fresh fetch from GitHub Pages CDN         │
└─────────────────────────────────────────────┘
```

---

## 2. How to Trigger a Version Bump Manually

```bash
# Option 1: run script directly
cd /path/to/repo
node .github/workflows/generate_version.js
git add version.json sw.js index.html
git commit -m "manual version bump"
git push

# Option 2: GitHub Actions UI
# Go to Actions → "Zero-Stale Cache — Version Bump on Deploy" → Run workflow
```

The script generates `version = YYYYMMDDHHMMSS` in IST (UTC+5:30).

---

## 3. sessionStorage Keys — Contents & TTL

| Key | Contents | TTL | Cleared by |
|-----|----------|-----|-----------|
| `__sr_merged_v11` | Complete_Jobs_Full_Data.json payload | 15 min | deploy detection, schema bump |
| `__ticker_sec_v2` | sections-index.json ticker data | 15 min | deploy detection, schema bump |
| `tsj_site_version` | Last known version string (localStorage) | persistent | schema bump |
| `tsj_data_version` | Schema version = `'8'` (localStorage) | persistent | manual only |
| `tsj_rv` | Recently viewed jobs array (localStorage) | persistent | schema bump |

**Schema version** is `DATA_SCHEMA_VER = '8'` in `tsj-version.js`. Bumping this triggers a one-time wipe of all stale keys on every user's first visit.

---

## 4. Debugging Cache Issues in Chrome DevTools

```
1. Open DevTools → Application tab

2. Check Service Worker:
   Application → Service Workers
   - Should show sw.js as "Activated and running"
   - "Source" column shows current SW_VERSION
   - Click "Update" to force re-fetch sw.js

3. Check Cache Storage:
   Application → Cache Storage
   - Should show ONLY caches matching current SW_VERSION:
     tsj-static-20260530XXXXXX
     tsj-pages-20260530XXXXXX
     tsj-data-20260530XXXXXX
     tsj-offline-20260530XXXXXX
   - If you see old versions (different timestamp) → old caches not deleted yet
   - Fix: click "Unregister" on the SW, then hard refresh

4. Clear everything manually:
   Application → Clear Storage → Clear site data
   (Nuclear option — forces full re-download)

5. Check version.json:
   Network tab → filter "version.json"
   - Should show 200 (not 304 / from cache)
   - Response body: { "version": "20260530XXXXXX", ... }

6. Console commands:
   TSJVersion.getVersion()    // current known version
   TSJVersion.forceUpdate()   // clear cache + reload
   TSJVersion.clearCache()    // clear without reload
   caches.keys().then(console.log)  // list all SW caches
```

---

## 5. GitHub Actions Auto-Deploy Flow

```
Developer pushes to main
         │
         ▼
deploy.yml triggers
         │
         ▼
node generate_version.js
  ├─ version = IST timestamp
  ├─ version.json ← written
  ├─ sw.js ← SW_VERSION replaced
  └─ *.html ← tsj-version.js/menu/push ?v= updated
         │
         ▼
git commit + push "[bot] Version bump vXXXXXX"
         │
         ▼
GitHub Pages serves new files
         │
         ▼ (user visits site)
tsj-version.js loads with new ?v= (fresh copy)
         │
         ├─ Boot check: localStorage version ≠ new version
         │  → sessionStorage.clear() IMMEDIATELY
         │  → data fetches get fresh JSON
         │
         ├─ SW registration: updateViaCache:'none'
         │  → browser re-fetches sw.js
         │  → new SW_VERSION → new cache names
         │  → old caches deleted on ACTIVATE
         │
         └─ SW sends SW_UPDATED → page reloads (800ms delay)
              → User sees fresh content
```

**Timeline:** User sees new content within ~30 seconds of push deploying on GitHub Pages.

---

## 6. Known Limitations on GitHub Pages

| Limitation | Workaround |
|-----------|-----------|
| No custom HTTP headers | Use `<meta http-equiv="Cache-Control">` in HTML (already present) |
| JS/CSS files cached 10 min by CDN | `?v=TIMESTAMP` query strings bypass CDN cache |
| version.json cached 10 min by CDN | `?_t=Date.now()` cache buster + `cache: 'no-store'` + SW intercepts |
| No server-side redirects | `_redirects` file (Netlify) / `404.html` trick (GitHub Pages) |
| SW scope limited to deploy path | Site is at domain apex → scope `/` works correctly |

**Important:** GitHub Pages serves `index.html` with `Cache-Control: no-cache` (validates with ETag), but serves JS/CSS with `max-age=600` (10 minutes). The `?v=TIMESTAMP` versioning is the primary defense against stale JS/CSS — the SW is the second layer.

---

## 7. Version Number Format

```
YYYYMMDDHHMMSS in IST (UTC+5:30)
Example: 20260530143000 = May 30, 2026 at 14:30:00 IST

This means:
- Each deploy gets a unique version
- Versions sort chronologically
- Easy to tell when a deploy happened
```

---

*Generated by Zero-Stale Cache Engine v8.0*
