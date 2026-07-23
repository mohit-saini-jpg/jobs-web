/* Shared Supabase Auth helper for /vle/login and /vle/dashboard.
   Loads @supabase/supabase-js from the same CDN + config.json pattern
   already used by script.js's CSC modal (ensureSupabaseClient), so no new
   loading pattern is introduced for this feature. */
(function (global) {
  var client = null;

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      if (document.querySelector('script[src="' + src + '"]')) { resolve(); return; }
      var s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  async function ensureClient() {
    if (client) return client;
    if (!global.supabase) {
      await loadScript('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2').catch(function () {});
    }
    if (!global.supabase) return null;
    var res = await fetch('/config.json', { cache: 'default' });
    var config = await res.json();
    if (!config || !config.supabase || !config.supabase.url || !config.supabase.anonKey) return null;
    client = global.supabase.createClient(config.supabase.url, config.supabase.anonKey);
    return client;
  }

  async function getSession() {
    var c = await ensureClient();
    if (!c) return null;
    var r = await c.auth.getSession();
    return (r && r.data && r.data.session) || null;
  }

  async function signIn(email, password) {
    var c = await ensureClient();
    if (!c) return { error: { message: 'Auth service unavailable' } };
    return c.auth.signInWithPassword({ email: email, password: password });
  }

  async function signOut() {
    var c = await ensureClient();
    if (c) await c.auth.signOut();
    location.href = '/vle/login/';
  }

  // Call at the top of /vle/dashboard/ — redirects to login if no session,
  // otherwise resolves with { session, profile } (profile = this VLE's
  // district/center row from vle_profiles).
  async function requireVleAuth() {
    var c = await ensureClient();
    if (!c) { location.href = '/vle/login/'; return null; }
    var session = await getSession();
    if (!session) { location.href = '/vle/login/'; return null; }
    var prof = await c
      .from('vle_profiles')
      .select('*')
      .eq('id', session.user.id)
      .maybeSingle();
    if (prof.error || !prof.data) {
      // Logged in but no matching vle_profiles row — admin hasn't finished
      // setting this account up yet.
      await signOut();
      return null;
    }
    return { session: session, profile: prof.data, client: c };
  }

  global.TsjVleAuth = {
    ensureClient: ensureClient,
    getSession: getSession,
    signIn: signIn,
    signOut: signOut,
    requireVleAuth: requireVleAuth,
  };
})(window);
