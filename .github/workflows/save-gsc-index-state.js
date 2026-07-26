#!/usr/bin/env node
/**
 * save-gsc-index-state.js — robust, race-safe commit+push of
 * data/gsc_index_state.json.
 *
 * Same technique as save-google-index-state.js (see that file for the full
 * incident writeup on why this repo never does a plain git-level rebase/
 * merge for small JSON state files written by scheduled workflows): a
 * SEMANTIC merge instead of a git-line merge. This file's shape is a flat
 * { urlPath: {indexed, verdict, lastChecked} } map, so the merge rule is
 * simply "per key, keep whichever side has the newer lastChecked" -- never
 * loses a real API result no matter how many processes push around the
 * same time, and there's no rebase/merge conflict state to get stuck in.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const STATE_REL_PATH = 'data/gsc_index_state.json';
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
  const merged = { ...(origin || {}) };
  for (const [url, entry] of Object.entries(mine || {})) {
    const existing = merged[url];
    if (!existing || String(entry.lastChecked || '') >= String(existing.lastChecked || '')) {
      merged[url] = entry;
    }
  }
  return merged;
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
    const total = Object.keys(merged).length;
    const idx = Object.values(merged).filter(e => e.indexed === true).length;
    run(`git commit -m "🔎 GSC index-status state (${stampIST} IST): ${total} URLs tracked, ${idx} indexed [skip ci]"`);

    try {
      run('git push origin main');
      console.log(`✅ gsc_index_state.json pushed (attempt ${attempt}/${MAX_ATTEMPTS}) — ${total} URLs tracked, ${idx} confirmed indexed.`);
      return;
    } catch (e) {
      console.log(`⚠️  Push attempt ${attempt}/${MAX_ATTEMPTS} failed — resyncing and retrying…`);
      if (attempt === MAX_ATTEMPTS) {
        console.error('❌ Push failed after all attempts — this run\'s GSC check results were NOT saved.');
        process.exit(1);
      }
      sleepSeconds(2 * attempt + Math.floor(Math.random() * 3));
    }
  }
}

main();
