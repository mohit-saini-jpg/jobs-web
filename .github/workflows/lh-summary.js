#!/usr/bin/env node
/**
 * lh-summary.js — parse Lighthouse CI output and:
 *   1. write a Markdown scoreboard to the GitHub Actions job summary
 *   2. flag a regression (perf < 0.85 OR LCP > 4000ms on any URL) and write an
 *      issue body so the workflow can open/update a GitHub issue
 *
 * Reads .lighthouseci/manifest.json (+ each run's LHR json) and links.json
 * (public report URLs from temporary-public-storage). Fails soft — a missing
 * manifest (e.g. site unreachable) never crashes the workflow.
 */
'use strict';
const fs = require('fs');
const path = require('path');

const DIR = '.lighthouseci';
const OUT = process.env.GITHUB_OUTPUT;
const SUMMARY = process.env.GITHUB_STEP_SUMMARY;

// Regression thresholds (open an issue only on a REAL drop, not minor jitter).
const PERF_ALERT = 0.85;   // performance category
const LCP_ALERT = 4000;    // ms

function setOutput(k, v) {
  if (OUT) fs.appendFileSync(OUT, `${k}=${v}\n`);
}
function writeSummary(md) {
  if (SUMMARY) fs.appendFileSync(SUMMARY, md + '\n');
  process.stdout.write(md + '\n');
}
function pct(n) { return n == null ? '—' : Math.round(n * 100); }
function ms(n) { return n == null ? '—' : Math.round(n) + ' ms'; }
function emoji(score, min) { return score == null ? '⚪' : score >= min ? '🟢' : score >= min - 0.1 ? '🟡' : '🔴'; }

function main() {
  const manifestPath = path.join(DIR, 'manifest.json');
  if (!fs.existsSync(manifestPath)) {
    writeSummary('### ⚡ Lighthouse Monitor\n\n> No results produced (site unreachable or run failed). No alert raised.');
    setOutput('regressed', 'false');
    return;
  }

  let manifest = [];
  try { manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8')); } catch (_) {}
  const reps = manifest.filter(m => m.isRepresentativeRun);

  let links = {};
  const linksPath = path.join(DIR, 'links.json');
  if (fs.existsSync(linksPath)) {
    try { links = JSON.parse(fs.readFileSync(linksPath, 'utf8')); } catch (_) {}
  }

  const rows = [];
  const alerts = [];
  for (const run of reps) {
    let lhr = {};
    try { lhr = JSON.parse(fs.readFileSync(run.jsonPath, 'utf8')); } catch (_) {}
    const cats = lhr.categories || {};
    const a = lhr.audits || {};
    const perf = cats.performance ? cats.performance.score : null;
    const seo = cats.seo ? cats.seo.score : null;
    const a11y = cats.accessibility ? cats.accessibility.score : null;
    const bp = cats['best-practices'] ? cats['best-practices'].score : null;
    const lcp = a['largest-contentful-paint'] ? a['largest-contentful-paint'].numericValue : null;
    const fcp = a['first-contentful-paint'] ? a['first-contentful-paint'].numericValue : null;
    const cls = a['cumulative-layout-shift'] ? a['cumulative-layout-shift'].numericValue : null;
    const tbt = a['total-blocking-time'] ? a['total-blocking-time'].numericValue : null;
    const url = run.url;
    const report = links[url];
    const short = url.replace('https://www.topsarkarijobs.com', '') || '/';

    rows.push(
      `| ${emoji(perf, 0.9)} \`${short}\` | **${pct(perf)}** | ${pct(seo)} | ${pct(a11y)} | ${pct(bp)} | ${ms(lcp)} | ${ms(fcp)} | ${cls == null ? '—' : cls.toFixed(3)} | ${ms(tbt)} |` +
      (report ? ` [report](${report}) |` : ' |')
    );

    if ((perf != null && perf < PERF_ALERT) || (lcp != null && lcp > LCP_ALERT)) {
      alerts.push(`- \`${short}\` — Performance **${pct(perf)}**, LCP **${ms(lcp)}**` + (report ? ` ([report](${report}))` : ''));
    }
  }

  const header =
    '### ⚡ Lighthouse Monitor (mobile, median of 3 runs)\n\n' +
    '| URL | Perf | SEO | A11y | BP | LCP | FCP | CLS | TBT | Report |\n' +
    '|-----|-----:|----:|-----:|---:|----:|----:|----:|----:|:------:|\n';
  writeSummary(header + rows.join('\n'));

  if (alerts.length) {
    const body =
      `## ⚠️ Lighthouse performance regression\n\n` +
      `One or more pages dropped below budget (Performance < ${PERF_ALERT * 100} or LCP > ${LCP_ALERT} ms) on mobile.\n\n` +
      alerts.join('\n') +
      `\n\n_Run: ${process.env.GITHUB_SERVER_URL || 'https://github.com'}/${process.env.GITHUB_REPOSITORY || ''}/actions/runs/${process.env.GITHUB_RUN_ID || ''}_\n` +
      `\nThresholds: alert on Perf < ${PERF_ALERT * 100} or LCP > ${LCP_ALERT} ms. Adjust in \`.github/workflows/lh-summary.js\`.`;
    fs.writeFileSync(path.join(DIR, 'issue-body.md'), body, 'utf8');
    setOutput('regressed', 'true');
    writeSummary('\n> 🔴 **Regression detected** — a tracking issue will be opened/updated.');
  } else {
    setOutput('regressed', 'false');
    writeSummary('\n> 🟢 All monitored pages within budget.');
  }
}

try { main(); } catch (e) {
  writeSummary('### ⚡ Lighthouse Monitor\n\n> Parser error: ' + e.message + ' — no alert raised.');
  setOutput('regressed', 'false');
}
