/* Public /vle/<district>/ page: renders the CSC/VLE profile card + live
   notice feed for window.__VLE_DISTRICT__. Runs entirely client-side after
   the static shell loads (async, non-blocking — same pattern as the job-page
   lead widget) so it never delays SSR/HTML render or hurts Core Web Vitals. */
(function () {
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function fmtDate(iso) {
    try {
      return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch (e) { return ''; }
  }

  function waLink(number, text) {
    var n = String(number || '').replace(/\D/g, '');
    if (n.length === 10) n = '91' + n;
    return 'https://wa.me/' + n + (text ? '?text=' + encodeURIComponent(text) : '');
  }

  function videoEmbedHtml(type, url) {
    if (!url) return '';
    if (type === 'youtube') {
      var id = (/(?:youtu\.be\/|shorts\/|v=)([a-zA-Z0-9_-]{6,})/.exec(url) || [])[1];
      if (!id) return '';
      return '<iframe src="https://www.youtube.com/embed/' + id + '" loading="lazy" allowfullscreen></iframe>';
    }
    if (type === 'instagram') {
      return '<iframe src="' + escapeHtml(url.replace(/\/?$/, '/')) + 'embed" loading="lazy" allowfullscreen></iframe>';
    }
    if (type === 'upload') {
      return '<video src="' + escapeHtml(url) + '" controls preload="none"></video>';
    }
    return '';
  }

  function renderProfile(mount, profile) {
    if (!profile) {
      mount.innerHTML =
        '<div class="vle-profile-card"><span class="badge">CSC NOTICE BOARD</span>' +
        '<h1>' + escapeHtml(window.__VLE_DISTRICT__) + ' District</h1>' +
        '<p class="sub">Is district ke liye abhi koi CSC partner register nahi hua hai.</p></div>';
      return;
    }
    mount.innerHTML =
      '<div class="vle-profile-card">' +
      '<span class="badge">CSC NOTICE BOARD</span>' +
      '<h1>' + escapeHtml(profile.center_name || (window.__VLE_DISTRICT__ + ' District')) + '</h1>' +
      '<p class="sub">Official local notices &amp; form-filling help from your nearest CSC partner</p>' +
      (profile.owner_name ? '<div class="row"><i class="fa-solid fa-user"></i> ' + escapeHtml(profile.owner_name) + '</div>' : '') +
      (profile.shop_address ? '<div class="row"><i class="fa-solid fa-location-dot"></i> ' + escapeHtml(profile.shop_address) + '</div>' : '') +
      (profile.contact_phone ? '<div class="row"><i class="fa-solid fa-phone"></i> ' + escapeHtml(profile.contact_phone) + '</div>' : '') +
      '</div>';
  }

  function postCard(post) {
    var media = '';
    if (post.image_url) media += '<img src="' + escapeHtml(post.image_url) + '" alt="' + escapeHtml(post.title) + '" loading="lazy">';
    var body = '<div class="body">';
    body += '<h2>' + escapeHtml(post.title) + '</h2>';
    if (post.description) body += '<p>' + escapeHtml(post.description) + '</p>';
    body += '<div class="time"><i class="fa-regular fa-clock"></i> ' + fmtDate(post.created_at) + '</div>';
    if (post.pdf_url) {
      body += '<a class="pdf-link" href="' + escapeHtml(post.pdf_url) + '" target="_blank" rel="noopener"><i class="fa-solid fa-file-pdf"></i> Official Notification (PDF)</a>';
    }
    var vid = videoEmbedHtml(post.video_type, post.video_url);
    if (vid) body += vid;
    var waText = 'Namaste, mujhe "' + post.title + '" ke baare mein jaankari chahiye — ' + location.href;
    body += '<div class="cta-row">';
    body += '<a class="cta-wa" href="' + waLink(post.whatsapp_number, waText) + '" target="_blank" rel="noopener"><i class="fa-brands fa-whatsapp"></i> ' + escapeHtml(post.cta_text || 'Ghar Baithe Form Bharwayein') + '</a>';
    body += '<button type="button" class="cta-share" data-share-title="' + escapeHtml(post.title) + '"><i class="fa-solid fa-share-nodes"></i> Share</button>';
    body += '</div></div>';
    return '<article class="vle-notice">' + media + body + '</article>';
  }

  function renderFeed(mount, posts) {
    if (!posts.length) {
      mount.innerHTML = '<div class="vle-feed-empty"><i class="fa-regular fa-folder-open"></i>Abhi is district ke liye koi active notice nahi hai.</div>';
      return;
    }
    mount.innerHTML = posts.map(postCard).join('');
    mount.querySelectorAll('.cta-share').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var title = btn.getAttribute('data-share-title');
        var url = location.href;
        var text = title + ' — ' + url;
        if (navigator.share) {
          navigator.share({ title: title, url: url }).catch(function () {});
        } else {
          window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(text), '_blank', 'noopener');
        }
      });
    });
  }

  async function init() {
    var district = window.__VLE_DISTRICT__;
    var profileMount = document.getElementById('vleProfileCard');
    var feedMount = document.getElementById('vleFeed');
    if (!district || !profileMount || !feedMount || !window.TsjVleAuth) return;

    var client = await window.TsjVleAuth.ensureClient();
    if (!client) {
      feedMount.innerHTML = '<div class="vle-feed-empty">Notice board load nahi ho paya, thodi der me try karein.</div>';
      return;
    }

    var profRes = await client.from('vle_profiles').select('*').eq('district', district).maybeSingle();
    renderProfile(profileMount, profRes.data || null);

    var todayIso = new Date().toISOString().slice(0, 10);
    var postsRes = await client
      .from('vle_posts')
      .select('*')
      .eq('district', district)
      .gte('expiry_date', todayIso)
      .order('created_at', { ascending: false });

    renderFeed(feedMount, postsRes.data || []);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
