/**
 * Zero-Stale Cache Engine — Version Bump Script v8.0
 * =====================================================
 * Run by GitHub Actions on EVERY deploy (also by auto-update-jobs.yml)
 *
 * What it does:
 * 1. Generates BUILD_VERSION = YYYYMMDDHHMMSS in IST (UTC+5:30)
 * 2. Writes version.json
 * 3. Patches sw.js: replaces SW_VERSION = '__BUILD_VERSION__' (or any existing value)
 * 4. Patches ALL .html files: updates ?v= for tsj-version.js, tsj-menu.js, tsj-push.js
 * 5. Logs every change
 * 6. Idempotent — safe to run multiple times
 * 7. Zero external dependencies (only fs, path)
 */

'use strict';

const fs   = require('fs');
const path = require('path');

// ── Generate IST timestamp (UTC+5:30) ────────────────────────────────
const now    = new Date();
const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;
const ist    = new Date(now.getTime() + IST_OFFSET_MS);
const pad    = n => String(n).padStart(2, '0');
const version = [
  ist.getUTCFullYear(),
  pad(ist.getUTCMonth() + 1),
  pad(ist.getUTCDate()),
  pad(ist.getUTCHours()),
  pad(ist.getUTCMinutes()),
  pad(ist.getUTCSeconds()),
].join('');
const builtISO = now.toISOString();

const ROOT = path.resolve(process.cwd());
let changedFiles = [];

// ── 1. Write version.json ─────────────────────────────────────────────
const versionPath = path.join(ROOT, 'version.json');
const versionData = { version, built: builtISO, site: 'topsarkarijobs.com' };
fs.writeFileSync(versionPath, JSON.stringify(versionData, null, 2) + '\n');
changedFiles.push('version.json');
console.log('✅ version.json →', version);

// ── 2. Patch sw.js — replace SW_VERSION ──────────────────────────────
const swPath = path.join(ROOT, 'sw.js');
if (fs.existsSync(swPath)) {
  let sw = fs.readFileSync(swPath, 'utf8');
  const swBefore = sw;
  // Matches: const SW_VERSION = 'anything'; OR '__BUILD_VERSION__'
  sw = sw.replace(
    /^const SW_VERSION\s*=\s*['"`][^'"`]*['"`];.*$/m,
    `const SW_VERSION = '${version}'; // auto-updated by generate_version.js`
  );
  if (sw !== swBefore) {
    fs.writeFileSync(swPath, sw);
    changedFiles.push('sw.js');
    console.log('✅ sw.js SW_VERSION →', version);
  } else {
    console.log('ℹ️  sw.js unchanged (version already set)');
  }
} else {
  console.warn('⚠️  sw.js not found');
}

// ── 3. Patch ALL HTML files ───────────────────────────────────────────
// Scripts to version: tsj-version.js, tsj-menu.js, tsj-push.js
// Strategy: update existing ?v=XXX, or add ?v=NEW if missing
function patchHtmlFile(filePath) {
  if (!fs.existsSync(filePath)) return false;
  let content = fs.readFileSync(filePath, 'utf8');
  const before = content;

  // tsj-version.js — update or add ?v=
  content = content
    .replace(/(<script[^>]+src="\/tsj-version\.js)\?v=[^"]*(")/g, `$1?v=${version}$2`)
    .replace(/(<script[^>]+src="\/tsj-version\.js")(?!\?)/g, `$1?v=${version}`);

  // tsj-menu.js — update existing ?v=, or ADD ?v= if missing
  content = content
    .replace(/(<script[^>]+src="\/tsj-menu\.js)\?v=[^"]*(")/g, `$1?v=${version}$2`)
    .replace(/(<script[^>]+src="\/tsj-menu\.js)("[ >"\/])/g, `$1?v=${version}$2`);

  // tsj-push.js — update or add ?v=
  content = content
    .replace(/(<script[^>]+src="\/tsj-push\.js)\?v=[^"]*(")/g, `$1?v=${version}$2`)
    .replace(/(<script[^>]+src="\/tsj-push\.js")(?!\?)/g, `$1?v=${version}`);

  if (content !== before) {
    fs.writeFileSync(filePath, content);
    return true;
  }
  return false;
}

// Find all HTML files in root + key subdirs
function findHtmlFiles(dir, depth) {
  if (depth === undefined) depth = 0;
  if (depth > 2) return [];
  let results = [];
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.name.startsWith('.') || entry.name === 'node_modules') continue;
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        // Only recurse into key dirs — skip jobs/ (3000+ files, no tsj-version.js)
        const skipDirs = ['jobs', 'fonts', 'icons', 'screenshots', 'splash', 'tools'];
        if (!skipDirs.includes(entry.name)) {
          results = results.concat(findHtmlFiles(fullPath, depth + 1));
        }
      } else if (entry.name.endsWith('.html')) {
        results.push(fullPath);
      }
    }
  } catch (e) {}
  return results;
}

const htmlFiles = findHtmlFiles(ROOT, 0);
let htmlPatched = 0;

for (const filePath of htmlFiles) {
  if (patchHtmlFile(filePath)) {
    const rel = path.relative(ROOT, filePath);
    console.log('✅ Patched:', rel);
    changedFiles.push(rel);
    htmlPatched++;
  }
}

// ── 4. Summary ────────────────────────────────────────────────────────
console.log('');
console.log('┌─────────────────────────────────────────────────┐');
console.log('│   Zero-Stale Cache Engine v8.0 — Version Bump  │');
console.log('├─────────────────────────────────────────────────┤');
console.log('│  Version (IST) : ' + version.padEnd(30) + '│');
console.log('│  Built (UTC)   : ' + builtISO.slice(0, 19).padEnd(30) + '│');
console.log('│  SW patched    : sw.js                          │');
console.log('│  HTML patched  : ' + String(htmlPatched + ' files').padEnd(30) + '│');
console.log('│  Total changes : ' + String(changedFiles.length + ' files').padEnd(30) + '│');
console.log('└─────────────────────────────────────────────────┘');
