// Tiny public status check for the "Form Filling Request" (CSC Partner)
// widget's site-wide kill switch — job-form-widget.js calls this before
// rendering the form. Backed by the site_settings table (see
// supabase/site_settings_migration.sql) so an admin can flip it from
// /vle/admin/ without a code push, instead of editing a file and redeploying.

const SUPABASE_URL = 'https://cykkclkfimmqbahanidg.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN5a2tjbGtmaW1tcWJhaGFuaWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNzYxODAsImV4cCI6MjA4MTY1MjE4MH0.iZEnetgYn7j0ltJyjhxUGZ3nCT7YMxGP3_Qd-agI1C0';

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  try {
    const r = await fetch(
      `${SUPABASE_URL}/rest/v1/site_settings?key=eq.jfw_enabled&select=value_bool`,
      { headers: { apikey: SUPABASE_ANON, Authorization: `Bearer ${SUPABASE_ANON}` } }
    );
    if (!r.ok) { res.status(200).json({ enabled: true }); return; } // fail open
    const rows = await r.json();
    const enabled = !rows.length || rows[0].value_bool !== false;
    res.status(200).json({ enabled });
  } catch (e) {
    res.status(200).json({ enabled: true }); // fail open on any error
  }
};
