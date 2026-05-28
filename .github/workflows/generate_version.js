/**
 * Zero-Stale Cache Engine — Version Bump Script v7.0
 * Run by GitHub Actions on EVERY deploy
 *
 * What it does:
 * 1. Generates a new timestamp-based version string (YYYYMMDDHHMMSS UTC)
 * 2. Updates version.json  ← fetched by tsj-version.js every 5 min
 * 3. Updates SW_VERSION in sw.js ← new SW gets unique cache names → old caches auto-deleted
 *
 * Usage: node .github/workflows/generate_version.js
 */

const fs   = require('fs');
const path = require('path');

// ── Generate version: YYYYMMDDHHMMSS (UTC) ───────────────────────────
const now     = new Date();
const pad     = n => String(n).padStart(2, '0');
const version = [
  now.getUTCFullYear(),
  pad(now.getUTCMonth() + 1),
  pad(now.getUTCDate()),
  pad(now.getUTCHours()),
  pad(now.getUTCMinutes()),
  pad(now.getUTCSeconds()),
].join('');
const builtISO = now.toISOString();

// ── 1. Write version.json ─────────────────────────────────────────────
const versionJson = { version, built: builtISO, site: 'topsarkarijobs.com' };
const versionPath = path.resolve(process.cwd(), 'version.json');
fs.writeFileSync(versionPath, JSON.stringify(versionJson, null, 2) + '\n');
console.log('✅ version.json ->', version);

// ── 2. Update SW_VERSION in sw.js ────────────────────────────────────
const swPath    = path.resolve(process.cwd(), 'sw.js');
let   swContent = fs.readFileSync(swPath, 'utf8');

// Replace const SW_VERSION line (handles any existing value or placeholder)
swContent = swContent.replace(
  /^const SW_VERSION\s*=\s*['"`][^'"`]*['"`];.*$/m,
  `const SW_VERSION = '${version}'; // auto-updated by generate_version.js`
);
fs.writeFileSync(swPath, swContent);
console.log('✅ sw.js SW_VERSION ->', version);

// ── 3. Summary ────────────────────────────────────────────────────────
console.log('');
console.log('┌─────────────────────────────────────────┐');
console.log('│  Zero-Stale Cache Engine v7.0 — Bump    │');
console.log('├─────────────────────────────────────────┤');
console.log('│  Version : ' + version.padEnd(29) + '│');
console.log('│  Built   : ' + builtISO.slice(0,19).padEnd(29) + '│');
console.log('│  Files   : version.json + sw.js         │');
console.log('└─────────────────────────────────────────┘');

// ── 4. Update tsj-version.js ?v= param in ALL HTML files ─────────────
const htmlFiles = ['index.html', 'job.html', 'state-job-detail.html'];
htmlFiles.forEach(filename => {
  const filePath = path.resolve(process.cwd(), filename);
  if (!fs.existsSync(filePath)) return;
  let fileContent = fs.readFileSync(filePath, 'utf8');
  // Update tsj-version.js version param
  const updated = fileContent.replace(
    /(<script[^>]+src="\/tsj-version\.js)[^"]*(")/g,
    `$1?v=${version}$2`
  );
  // Also add ?v= if missing entirely
  const updated2 = updated.replace(
    /(<script[^>]+src="\/tsj-version\.js")(?!\?)/g,
    `$1?v=${version}`
  );
  if (updated2 !== fileContent) {
    fs.writeFileSync(filePath, updated2);
    console.log(`✅ ${filename} tsj-version.js param ->`, version);
  }
});
