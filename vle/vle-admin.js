/* /vle/admin/ — pending-VLE approval queue.
   Gate: must be logged in via Supabase Auth AND present in the
   admin_users allow-list (see supabase/vle_signup_approval_migration.sql
   for how to add yourself as an admin).
   Approve sets is_approved=true. Reject deletes the profile row (frees
   the slot for someone else) — it does NOT delete the underlying auth
   account, since that needs a service-role key this static site never
   exposes client-side; the admin can remove the auth user separately via
   the Supabase Dashboard if needed. */
(function () {
  function $(id) { return document.getElementById(id); }
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmtDate(iso) {
    try { return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }); }
    catch (e) { return ''; }
  }

  var client = null;

  function showMsg(el, text, ok) {
    el.textContent = text;
    el.className = 'vle-msg show ' + (ok ? 'ok' : 'err');
  }

  function renderPending(list) {
    var mount = $('vlePendingList');
    $('vlePendingCount').textContent = list.length;
    if (!list.length) {
      mount.innerHTML = '<div class="vle-empty">Abhi koi naya VLE approval ke liye pending nahi hai.</div>';
      return;
    }
    mount.innerHTML = list.map(function (p) {
      return '<div class="vle-post-item" data-id="' + p.id + '">' +
        '<div class="body">' +
        '<h3>' + escapeHtml(p.center_name) + '</h3>' +
        '<p>' + escapeHtml(p.district) + ', ' + escapeHtml(p.state) + ' — Slot ' + p.slot + '</p>' +
        '<div class="meta">' +
        (p.owner_name ? '<span>' + escapeHtml(p.owner_name) + '</span>' : '') +
        (p.contact_phone ? '<span><i class="fa-solid fa-phone"></i> ' + escapeHtml(p.contact_phone) + '</span>' : '') +
        (p.whatsapp_number ? '<span><i class="fa-brands fa-whatsapp"></i> ' + escapeHtml(p.whatsapp_number) + '</span>' : '') +
        '<span>' + fmtDate(p.created_at) + '</span>' +
        '</div>' +
        (p.shop_address ? '<p style="margin-top:4px">' + escapeHtml(p.shop_address) + '</p>' : '') +
        '</div>' +
        '<div class="vle-post-actions" style="flex-direction:column">' +
        '<button class="vle-icon-btn vle-approve-btn" title="Approve"><i class="fa-solid fa-check" style="color:#16a34a"></i></button>' +
        '<button class="vle-icon-btn danger vle-reject-btn" title="Reject"><i class="fa-solid fa-xmark"></i></button>' +
        '</div>' +
        '</div>';
    }).join('');

    mount.querySelectorAll('.vle-approve-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { setStatus(btn.closest('.vle-post-item'), true); });
    });
    mount.querySelectorAll('.vle-reject-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { setStatus(btn.closest('.vle-post-item'), false); });
    });
  }

  async function loadPending() {
    var res = await client.from('vle_profiles').select('*').eq('is_approved', false).order('created_at', { ascending: true });
    renderPending(res.data || []);
  }

  async function setStatus(itemEl, approve) {
    var id = itemEl.getAttribute('data-id');
    if (!approve && !confirm('Ye VLE signup reject/remove kar dein?')) return;
    itemEl.style.opacity = '.5';
    if (approve) await client.from('vle_profiles').update({ is_approved: true }).eq('id', id);
    else await client.from('vle_profiles').delete().eq('id', id);
    loadPending();
  }

  async function checkAdmin(session) {
    var chk = await client.from('admin_users').select('id').eq('id', session.user.id).maybeSingle();
    return !!(chk.data && chk.data.id);
  }

  function showApp() {
    $('vleAdminLoadingScreen').style.display = 'none';
    $('vleAdminLoginScreen').style.display = 'none';
    $('vleAdminApp').style.display = '';
    loadPending();
  }

  async function boot() {
    client = await window.TsjVleAuth.ensureClient();
    if (!client) { $('vleAdminLoadingScreen').innerHTML = 'Auth service unavailable.'; return; }
    var session = await window.TsjVleAuth.getSession();
    if (session && await checkAdmin(session)) { showApp(); return; }
    if (session) {
      // Logged in but not an admin — sign out so the login form is clean.
      await client.auth.signOut();
    }
    $('vleAdminLoadingScreen').style.display = 'none';
    $('vleAdminLoginScreen').style.display = '';
  }

  document.getElementById('vleAdminLoginForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    var email = $('vleAdminEmail').value.trim();
    var password = $('vleAdminPassword').value;
    var msg = $('vleAdminLoginMsg');
    var res = await window.TsjVleAuth.signIn(email, password);
    if (res.error) { showMsg(msg, res.error.message, false); return; }
    if (!(await checkAdmin(res.data.session))) {
      showMsg(msg, 'Ye account admin list mein nahi hai.', false);
      await client.auth.signOut();
      return;
    }
    showApp();
  });

  document.getElementById('vleAdminLogoutBtn').addEventListener('click', async function () {
    if (client) await client.auth.signOut();
    location.href = '/vle/admin/';
  });

  boot();
})();
