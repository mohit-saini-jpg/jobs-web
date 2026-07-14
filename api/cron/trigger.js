// Triggers a GitHub Actions workflow immediately via the GitHub REST API,
// bypassing GitHub's own `schedule:` cron trigger — which routinely fires
// 2-4 hours late on this repo because GitHub queues scheduled workflows
// behind everyone else's crons during high-load minutes.
//
// Invoked by a Vercel Cron Job (see vercel.json `crons`), which runs on
// Vercel's own scheduler — separate infrastructure from GitHub Actions'
// scheduler, so it isn't subject to the same congestion.
//
// The workflow's own internal `schedule:` cron is intentionally left in
// place as a fallback: if this endpoint or the PAT ever breaks, the
// workflow still eventually runs on its own (just possibly late), rather
// than not running at all.

const OWNER = 'mohit-saini-jpg';
const REPO = 'jobs-web';
const REF = 'main';

// Only these workflow files may be dispatched — the `workflow` query param
// can never be used to trigger anything else, even if CRON_SECRET leaked.
const ALLOWED_WORKFLOWS = new Set([
  'scraper-fja-education.yml',
  'auto-update-jobs.yml',
  'check-broken-links.yml',
  'ai-nightly.yml',
  'ai-patch-html.yml',
  'seo-guardian-fullscan.yml',
  'google-index-daily.yml',
]);

module.exports = async function handler(req, res) {
  // Vercel sends this header automatically on cron-invoked requests when
  // CRON_SECRET is configured — https://vercel.com/docs/cron-jobs/manage-cron-jobs#securing-cron-jobs
  const authHeader = req.headers['authorization'];
  if (!process.env.CRON_SECRET || authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    res.status(401).json({ error: 'unauthorized' });
    return;
  }

  const workflow = String(req.query.workflow || '');
  if (!ALLOWED_WORKFLOWS.has(workflow)) {
    res.status(400).json({ error: 'unknown workflow', workflow });
    return;
  }

  const token = process.env.GITHUB_DISPATCH_TOKEN;
  if (!token) {
    res.status(500).json({ error: 'GITHUB_DISPATCH_TOKEN not configured' });
    return;
  }

  let ghRes;
  try {
    ghRes = await fetch(
      `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${workflow}/dispatches`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ref: REF }),
      }
    );
  } catch (e) {
    res.status(502).json({ error: 'github request failed', detail: String(e) });
    return;
  }

  if (ghRes.status === 204) {
    res.status(200).json({ ok: true, workflow, dispatchedAt: new Date().toISOString() });
    return;
  }

  const detail = await ghRes.text();
  res.status(502).json({ error: 'github dispatch failed', status: ghRes.status, detail });
};
