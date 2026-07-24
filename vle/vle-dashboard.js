/* /vle/dashboard/ logic: auth gate, post create/edit/delete, client-side
   image compression, and direct-to-R2 uploads via presigned URLs. */
(function () {
  var state = { client: null, session: null, profile: null, editingId: null, files: {} };

  function $(id) { return document.getElementById(id); }

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function showMsg(el, text, ok) {
    el.textContent = text;
    el.className = 'vle-msg show ' + (ok ? 'ok' : 'err');
  }

  // ── Image compression: resize to max 1600px on the long edge, then
  // binary-search WebP quality to land at/under ~150KB (same approach as
  // tools/image/compress-image.html's encodeTarget). ──────────────────────
  function loadImage(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () { resolve(img); };
      img.onerror = reject;
      img.src = url;
    });
  }

  function canvasToBlobP(cv, mime, q) {
    return new Promise(function (resolve, reject) {
      cv.toBlob(function (b) { b ? resolve(b) : reject(new Error('encode failed')); }, mime, q);
    });
  }

  async function compressToWebp(file, targetKB) {
    var img = await loadImage(file);
    var maxSide = 1600;
    var w = img.naturalWidth, h = img.naturalHeight;
    if (Math.max(w, h) > maxSide) {
      var scale = maxSide / Math.max(w, h);
      w = Math.round(w * scale); h = Math.round(h * scale);
    }
    var cv = document.createElement('canvas');
    cv.width = w; cv.height = h;
    var ctx = cv.getContext('2d');
    ctx.drawImage(img, 0, 0, w, h);

    var target = targetKB * 1024, lo = 0.05, hi = 0.92, best = null;
    for (var i = 0; i < 8; i++) {
      var q = (lo + hi) / 2;
      var b = await canvasToBlobP(cv, 'image/webp', q);
      if (b.size <= target) { best = b; lo = q; } else { hi = q; }
    }
    if (!best) best = await canvasToBlobP(cv, 'image/webp', 0.05);
    return best;
  }

  // ── Upload flow: ask api/vle-upload-signature for a signed Cloudinary
  // upload slot, then POST the bytes straight to Cloudinary (never through
  // our own server — same reasoning as the earlier R2 design, just with
  // Cloudinary's signed-upload mechanism instead of a presigned PUT URL). ──
  async function uploadToCloudinary(blob, folder, fileName) {
    var token = state.session.access_token;
    var sigRes = await fetch('/api/vle-upload-signature', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
      body: JSON.stringify({ folder: folder }),
    });
    if (!sigRes.ok) throw new Error((await sigRes.json().catch(function () { return {}; })).error || 'upload signature failed');
    var sig = await sigRes.json();

    var form = new FormData();
    form.append('file', blob, fileName);
    form.append('api_key', sig.apiKey);
    form.append('timestamp', sig.timestamp);
    form.append('folder', sig.folder);
    form.append('signature', sig.signature);

    var up = await fetch('https://api.cloudinary.com/v1_1/' + sig.cloudName + '/auto/upload', { method: 'POST', body: form });
    if (!up.ok) throw new Error('Cloudinary upload failed');
    var result = await up.json();
    return { url: result.secure_url, publicId: result.public_id };
  }

  // ── File-picker wiring for image / pdf / video-upload boxes ────────────
  function wireUploadBox(boxId, textId, inputId, accept, onFile) {
    var box = $(boxId), text = $(textId), input = $(inputId);
    box.addEventListener('click', function () { input.click(); });
    input.addEventListener('change', async function () {
      var f = input.files[0];
      if (!f) return;
      box.classList.add('has-file');
      text.textContent = f.name + ' ✓';
      await onFile(f);
    });
  }

  function setupForm() {
    wireUploadBox('vleImageBox', 'vleImageBoxText', 'vleImageInput', 'image/*', async function (f) {
      $('vleImageBoxText').textContent = 'Compressing…';
      try {
        var blob = await compressToWebp(f, 150);
        state.files.image = { blob: blob, type: 'image/webp', name: 'photo.webp' };
        $('vleImageBoxText').textContent = f.name + ' (' + Math.round(blob.size / 1024) + 'KB) ✓';
      } catch (e) {
        $('vleImageBoxText').textContent = 'Compression failed, try another photo';
        $('vleImageBox').classList.remove('has-file');
      }
    });

    wireUploadBox('vlePdfBox', 'vlePdfBoxText', 'vlePdfInput', 'application/pdf', async function (f) {
      if (f.size > 15 * 1024 * 1024) { $('vlePdfBoxText').textContent = 'PDF 15MB se bada hai'; return; }
      state.files.pdf = { blob: f, type: 'application/pdf', name: f.name };
    });

    wireUploadBox('vleVideoBox', 'vleVideoBoxText', 'vleVideoInput', 'video/mp4', async function (f) {
      if (f.size > 60 * 1024 * 1024) { $('vleVideoBoxText').textContent = 'Video 60MB se bada hai'; return; }
      state.files.video = { blob: f, type: 'video/mp4', name: f.name };
    });

    $('vleVideoMode').addEventListener('change', function () {
      var mode = this.value;
      $('vleVideoLinkWrap').style.display = (mode === 'youtube' || mode === 'instagram') ? '' : 'none';
      $('vleVideoUploadWrap').style.display = (mode === 'upload') ? '' : 'none';
    });

    $('vleExpiryPreset').addEventListener('change', function () {
      $('vleExpiryCustomWrap').style.display = this.value === 'custom' ? '' : 'none';
    });

    $('vleCancelEditBtn').addEventListener('click', resetForm);
    $('vlePostForm').addEventListener('submit', handleSubmit);
    $('vleLogoutBtn').addEventListener('click', function () { window.TsjVleAuth.signOut(); });
  }

  function resetForm() {
    state.editingId = null;
    state.files = {};
    $('vlePostForm').reset();
    $('vlePostId').value = '';
    $('vleFormHeading').innerHTML = '<i class="fa-solid fa-bullhorn"></i> New Notice Post Karein';
    $('vlePostSubmitBtn').innerHTML = '<i class="fa-solid fa-paper-plane"></i> Post Karein';
    $('vleCancelEditBtn').style.display = 'none';
    ['vleImageBox', 'vlePdfBox', 'vleVideoBox'].forEach(function (id) { $(id).classList.remove('has-file'); });
    $('vleImageBoxText').textContent = 'Tap to select photo';
    $('vlePdfBoxText').textContent = 'Tap to select PDF';
    $('vleVideoBoxText').textContent = 'Tap to select video (max 60MB)';
    $('vleVideoLinkWrap').style.display = 'none';
    $('vleVideoUploadWrap').style.display = 'none';
    $('vleExpiryCustomWrap').style.display = 'none';
    $('vleWhatsapp').value = (state.profile && state.profile.whatsapp_number) || '';
  }

  function computeExpiryDate() {
    var preset = $('vleExpiryPreset').value;
    if (preset === 'custom') return $('vleExpiryCustom').value || null;
    var d = new Date();
    d.setDate(d.getDate() + parseInt(preset, 10));
    return d.toISOString().slice(0, 10);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    var msg = $('vlePostMsg');
    var btn = $('vlePostSubmitBtn');

    var title = $('vleTitle').value.trim();
    var whatsapp = $('vleWhatsapp').value.trim();
    if (!title) { showMsg(msg, 'Post Title zaroori hai.', false); return; }
    if (!/^[6-9][0-9]{9}$/.test(whatsapp)) { showMsg(msg, 'Sahi 10-digit WhatsApp number daalein.', false); return; }
    var expiry = computeExpiryDate();
    if (!expiry) { showMsg(msg, 'Expiry date select karein.', false); return; }

    var videoMode = $('vleVideoMode').value;
    var videoLink = $('vleVideoLink').value.trim();
    if ((videoMode === 'youtube' || videoMode === 'instagram') && !videoLink) {
      showMsg(msg, 'Video link daalein ya "No video" select karein.', false); return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading…';

    try {
      var post = {
        vle_id: state.session.user.id,
        state: state.profile.state,
        district: state.profile.district,
        slot: state.profile.slot,
        title: title,
        description: $('vleDesc').value.trim(),
        cta_text: $('vleCta').value.trim() || 'Ghar Baithe Form Bharwayein',
        whatsapp_number: whatsapp,
        expiry_date: expiry,
      };

      if (state.files.image) {
        var imgUp = await uploadToCloudinary(state.files.image.blob, 'images', state.files.image.name);
        post.image_url = imgUp.url; post.image_public_id = imgUp.publicId;
      }
      if (state.files.pdf) {
        var pdfUp = await uploadToCloudinary(state.files.pdf.blob, 'pdfs', state.files.pdf.name);
        post.pdf_url = pdfUp.url; post.pdf_public_id = pdfUp.publicId;
      }
      if (videoMode === 'upload' && state.files.video) {
        post.video_type = 'upload';
        var vidUp = await uploadToCloudinary(state.files.video.blob, 'videos', state.files.video.name);
        post.video_url = vidUp.url; post.video_public_id = vidUp.publicId;
      } else if (videoMode === 'youtube' || videoMode === 'instagram') {
        post.video_type = videoMode;
        post.video_url = videoLink;
      } else if (videoMode === '') {
        post.video_type = null;
        post.video_url = null;
      }

      var res;
      if (state.editingId) {
        res = await state.client.from('vle_posts').update(post).eq('id', state.editingId).select();
      } else {
        res = await state.client.from('vle_posts').insert(post).select();
      }
      if (res.error) throw res.error;

      showMsg(msg, state.editingId ? 'Post update ho gaya!' : 'Post live ho gaya!', true);
      resetForm();
      loadPosts();
    } catch (err) {
      showMsg(msg, 'Error: ' + (err && err.message ? err.message : 'kuch galat ho gaya'), false);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Post Karein';
    }
  }

  function startEdit(post) {
    state.editingId = post.id;
    state.files = {};
    $('vlePostId').value = post.id;
    $('vleTitle').value = post.title || '';
    $('vleDesc').value = post.description || '';
    $('vleCta').value = post.cta_text || 'Ghar Baithe Form Bharwayein';
    $('vleWhatsapp').value = post.whatsapp_number || '';
    $('vleExpiryPreset').value = 'custom';
    $('vleExpiryCustomWrap').style.display = '';
    $('vleExpiryCustom').value = post.expiry_date || '';
    $('vleVideoMode').value = post.video_type || '';
    $('vleVideoMode').dispatchEvent(new Event('change'));
    $('vleVideoLink').value = (post.video_type === 'youtube' || post.video_type === 'instagram') ? (post.video_url || '') : '';
    if (post.image_url) { $('vleImageBox').classList.add('has-file'); $('vleImageBoxText').textContent = 'Current photo kept (naya select karein to badalne ke liye)'; }
    if (post.pdf_url) { $('vlePdfBox').classList.add('has-file'); $('vlePdfBoxText').textContent = 'Current PDF kept (naya select karein to badalne ke liye)'; }
    $('vleFormHeading').innerHTML = '<i class="fa-solid fa-pen"></i> Post Edit Karein';
    $('vlePostSubmitBtn').innerHTML = '<i class="fa-solid fa-check"></i> Update Karein';
    $('vleCancelEditBtn').style.display = '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function deletePost(post) {
    if (!confirm('"' + post.title + '" delete karein? Ye wapas nahi hoga.')) return;
    var del = await state.client.from('vle_posts').delete().eq('id', post.id);
    if (del.error) { alert('Delete nahi ho paya: ' + del.error.message); return; }

    var mediaItems = [
      post.image_public_id ? { publicId: post.image_public_id, folder: 'images' } : null,
      post.pdf_public_id ? { publicId: post.pdf_public_id, folder: 'pdfs' } : null,
      (post.video_type === 'upload' && post.video_public_id) ? { publicId: post.video_public_id, folder: 'videos' } : null,
    ].filter(Boolean);
    if (mediaItems.length) {
      fetch('/api/vle-delete-media', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + state.session.access_token },
        body: JSON.stringify({ items: mediaItems }),
      }).catch(function () {});
    }
    loadPosts();
  }

  function postListItem(post) {
    var expired = post.expiry_date < new Date().toISOString().slice(0, 10);
    return '<div class="vle-post-item" data-id="' + post.id + '">' +
      (post.image_url ? '<img src="' + escapeHtml(post.image_url) + '" alt="">' : '<div style="width:56px;height:56px;border-radius:8px;background:#f1f5f9;flex:none;display:flex;align-items:center;justify-content:center;color:#94a3b8"><i class="fa-solid fa-bullhorn"></i></div>') +
      '<div class="body">' +
      '<h3>' + escapeHtml(post.title) + '</h3>' +
      (post.description ? '<p>' + escapeHtml(post.description.slice(0, 80)) + '</p>' : '') +
      '<div class="meta"><span' + (expired ? ' class="expired"' : '') + '>' + (expired ? 'Expired' : 'Active') + ' · till ' + post.expiry_date + '</span></div>' +
      '</div>' +
      '<div class="vle-post-actions">' +
      '<button type="button" class="vle-icon-btn vle-edit-btn" aria-label="Edit"><i class="fa-solid fa-pen"></i></button>' +
      '<button type="button" class="vle-icon-btn danger vle-delete-btn" aria-label="Delete"><i class="fa-solid fa-trash"></i></button>' +
      '</div></div>';
  }

  async function loadPosts() {
    var mount = $('vlePostList');
    var res = await state.client.from('vle_posts').select('*').eq('vle_id', state.session.user.id).order('created_at', { ascending: false });
    if (res.error) { mount.innerHTML = '<div class="vle-empty">Posts load nahi ho paye.</div>'; return; }
    var posts = res.data || [];
    if (!posts.length) { mount.innerHTML = '<div class="vle-empty">Abhi tak koi post nahi hai — upar se pehla notice post karein.</div>'; return; }
    mount.innerHTML = posts.map(postListItem).join('');
    mount.querySelectorAll('.vle-post-item').forEach(function (el) {
      var id = Number(el.getAttribute('data-id'));
      var post = posts.filter(function (p) { return p.id === id; })[0];
      el.querySelector('.vle-edit-btn').addEventListener('click', function () { startEdit(post); });
      el.querySelector('.vle-delete-btn').addEventListener('click', function () { deletePost(post); });
    });
  }

  function setupProfileCompletionForm(client, userId) {
    var mount = $('vleCpProfileFields');
    mount.innerHTML = window.TsjVleSignup.fieldsHtml();
    window.TsjVleSignup.wireDropdowns(mount);
    var form = $('vleCompleteProfileForm');
    var msg = $('vleCpMsg');
    var btn = $('vleCpSubmitBtn');
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Save ho raha hai…';
      var fields = window.TsjVleSignup.readFields(mount);
      var res = await window.TsjVleSignup.createVleProfile(client, userId, fields);
      if (res.error) {
        showMsg(msg, res.error.message, false);
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Profile Save Karein';
        return;
      }
      showMsg(msg, 'Profile save ho gayi! Admin approval ka wait karein…', true);
      setTimeout(function () { location.reload(); }, 1500);
    });
  }

  async function init() {
    var auth = await window.TsjVleAuth.requireVleAuth();
    if (!auth) return;
    state.client = auth.client;
    state.session = auth.session;

    $('vleLoadingScreen').style.display = 'none';

    if (auth.needsProfile) {
      $('vleNeedsProfileScreen').style.display = '';
      setupProfileCompletionForm(auth.client, auth.session.user.id);
      return;
    }
    if (auth.pending) {
      $('vlePendingScreen').style.display = '';
      $('vlePendingLogoutBtn').addEventListener('click', function () { window.TsjVleAuth.signOut(); });
      return;
    }

    state.profile = auth.profile;
    $('vleApp').style.display = '';
    $('vleCenterName').textContent = state.profile.center_name || 'VLE Partner';
    $('vleDistrictName').textContent = state.profile.district + ' District, ' + state.profile.state +
      (state.profile.slot > 1 ? ' (CSC Partner ' + state.profile.slot + ')' : '');
    $('vleWhatsapp').value = state.profile.whatsapp_number || '';

    setupForm();
    loadPosts();
  }

  init();
})();
