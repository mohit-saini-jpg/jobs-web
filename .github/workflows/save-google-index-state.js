#!/usr/bin/env node
/**
 * save-google-index-state.js — robust, race-safe commit+push of
 * data/google_index_state.json.
 *
 * WHY THIS EXISTS (2026-07-16): the previous approach used git-level
 * rebase/merge (`git rebase origin/main` → on failure, `git rebase --abort`
 * + `git merge -X ours origin/main`) to reconcile concurrent pushes. On
 * 2026-07-16 that failed 5 times in a row (one attempt even hit "Please
 * tell me who you are" — a git identity edge case in the merge fallback
 * path) and the job exited 1 WITHOUT saving state. The consequence: a real,
 * successful 200-URL Google Indexing API submission (Google's actual
 * server-side quota was genuinely consumed) was never recorded in
 * done_slugs/submitted_today. An hour later the scheduled run — unaware
 * the day's quota was already spent — ran again, got a 429 after a single
 * URL, and the guard that's supposed to prevent this exact double-run
 * (skip-daily-duplicate) couldn't help because it only checks for a prior
 * SUCCESS today, and the first run had reported failure (on the git step,
 * not the actual submission).
 *
 * Fix: never touch git's line-based conflict machinery for this file at
 * all. This file has a simple, known shape — do a SEMANTIC (JSON-level)
 * merge: union the URL lists with whatever is on origin right now, then
 * `git reset --hard origin/main` (always a clean base, never a conflict
 * state) and recommit the merged result. Retry that whole cycle a bounded
 * number of times if another push lands in between. Content is never lost
 * regardless of how many processes push around the same time, and there is
 * no rebase/merge state to get stuck in.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const STATE_REL_PATH = 'data/google_index_state.json';
const MAX_ATTEMPTS = 8;

function run(cmd) {
  return execSync(cmd, { encoding: 'utf8' });
}

function readLocalState() {
  return JSON.parse(fs.readFileSync(STATE_REL_PATH, 'utf8'));
}

function readOriginState() {
  try {
    return JSON.parse(run(`git show origin/main:${STATE_REL_PATH}`));
  } catch (e) {
    return null; // doesn't exist on origin yet, or not parseable — treat as empty
  }
}

function mergeStates(mine, origin) {
  const today = mine.date;
  const baseToday = origin && origin.date === today ? origin : null;
  const submittedToday = Array.from(new Set([
    ...((baseToday && baseToday.submitted_today) || []),
    ...(mine.submitted_today || []),
  ]));
  // done_slugs is the PERMANENT cumulative record (never reset daily) —
  // union with origin regardless of origin's `date`, so a same-day OR a
  // prior-day origin write is never lost.
  const doneSlugs = Array.from(new Set([
    ...((origin && origin.done_slugs) || []),
    ...(mine.done_slugs || []),
  ]));
  return {
    date: today,
    count_today: submittedToday.length,
    submitted_today: submittedToday,
    done_slugs: doneSlugs,
  };
}

function setGitIdentity() {
  run('git config user.name "github-actions[bot]"');
  run('git config user.email "github-actions[bot]@users.noreply.github.com"');
}

function sleepSeconds(s) {
  execSync(`sleep ${s}`);
}

function main() {
  if (!fs.existsSync(STATE_REL_PATH)) {
    console.log('No state file present — nothing to save.');
    return;
  }
  const mine = readLocalState();
  setGitIdentity();

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    run('git fetch origin main');
    const origin = readOriginState();
    const merged = mergeStates(mine, origin);

    // Always reset to the current origin tip first — guarantees a clean
    // fast-forward-only commit, never a conflict.
    run('git reset --hard origin/main');
    fs.mkdirSync(path.dirname(STATE_REL_PATH), { recursive: true });
    fs.writeFileSync(STATE_REL_PATH, JSON.stringify(merged));
    run(`git add ${STATE_REL_PATH}`);

    const changed = run(`git status --porcelain -- ${STATE_REL_PATH}`).trim().length > 0;
    if (!changed) {
      console.log('✅ State already up to date on origin — nothing new to push.');
      return;
    }

    const stampIST = new Date(Date.now() + 5.5 * 3600 * 1000)
      .toISOString().replace('T', ' ').slice(0, 16);
    run(`git commit -m "🔎 Google index state (${stampIST} IST) [skip ci]"`);

    try {
      run('git push origin main');
      console.log(
        `✅ Google-index state pushed (attempt ${attempt}/${MAX_ATTEMPTS}) — ` +
        `${merged.submitted_today.length} submitted today, ${merged.done_slugs.length} total ever submitted.`
      );
      return;
    } catch (e) {
      console.log(`⚠️  Push attempt ${attempt}/${MAX_ATTEMPTS} failed — resyncing and retrying…`);
      if (attempt === MAX_ATTEMPTS) {
        console.error('❌ Push failed after all attempts — today\'s submission record was NOT saved.');
        process.exit(1);
      }
      sleepSeconds(2 * attempt + Math.floor(Math.random() * 3));
    }
  }
}

main();
