/* Shared custom picker for the "Exam/Job Preset" and "Quick Size Preset"
   <select><optgroup> dropdowns used by photo-editor.html, image-resizer.html
   and signature-resizer.html.

   WHY: a native <select> with many <optgroup>s renders fine on desktop
   Chrome (bold indented group headers), but on mobile (Android's native
   picker dialog especially) group headers, the placeholder option, and
   real options all end up looking visually similar in a long flat list —
   users can't tell what's a category vs. a selectable job. CSS can't fix
   this because mobile OSes render native <select> popups themselves, not
   the page's styles.

   This keeps the ORIGINAL <select> in the DOM untouched (hidden, not
   removed) so every existing call site that reads sel.value /
   sel.options[sel.selectedIndex].getAttribute('data-w') etc. keeps working
   with zero changes elsewhere — it just also gets a custom, searchable,
   clearly-grouped bottom-sheet/modal picker wired to stay in sync with it. */
(function () {
  var styleInjected = false;
  function injectStyle() {
    if (styleInjected) return;
    styleInjected = true;
    var css = '' +
      '.preset-picker-trigger .ppt-label{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;text-align:left}' +
      '.preset-picker-overlay{position:fixed;inset:0;background:rgba(15,23,42,.5);z-index:9999;display:flex;align-items:flex-end;justify-content:center;padding:0}' +
      '@media(min-width:640px){.preset-picker-overlay{align-items:center;padding:20px}}' +
      '.preset-picker-sheet{background:#fff;width:100%;max-width:520px;max-height:82vh;border-radius:16px 16px 0 0;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 -4px 30px rgba(0,0,0,.2)}' +
      '@media(min-width:640px){.preset-picker-sheet{border-radius:16px;max-height:76vh;box-shadow:0 10px 40px rgba(0,0,0,.25)}}' +
      '.preset-picker-head{padding:14px 16px 12px;border-bottom:1px solid #e2e8f0;flex:none}' +
      '.preset-picker-head .pph-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}' +
      '.preset-picker-head h3{margin:0;font-size:1rem;font-weight:800;color:#0f172a}' +
      '.preset-picker-x{background:#f1f5f9;border:none;width:30px;height:30px;border-radius:50%;font-size:1.1rem;line-height:1;color:#64748b;cursor:pointer}' +
      '.preset-picker-search{width:100%;padding:10px 12px;border:1.5px solid #e2e8f0;border-radius:8px;font-size:.9rem;font-family:inherit}' +
      '.preset-picker-list{overflow-y:auto;flex:1;padding:4px 0}' +
      '.preset-picker-group{padding:11px 16px 5px;font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:#64748b;background:#f8fafc;position:sticky;top:0}' +
      '.preset-picker-item{padding:12px 16px;font-size:.88rem;color:#1e293b;cursor:pointer;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;gap:8px}' +
      '.preset-picker-item:hover,.preset-picker-item:active{background:#eff6ff}' +
      '.preset-picker-item.active{background:#eff6ff;color:#2563eb;font-weight:700}' +
      '.preset-picker-empty{padding:34px 16px;text-align:center;color:#94a3b8;font-size:.86rem}';
    var s = document.createElement('style');
    s.textContent = css;
    document.head.appendChild(s);
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function buildGroups(sel) {
    var groups = [];
    Array.prototype.forEach.call(sel.children, function (node) {
      if (node.tagName === 'OPTGROUP') {
        var g = { label: node.label, items: [] };
        Array.prototype.forEach.call(node.children, function (opt) {
          g.items.push({ value: opt.value, text: opt.textContent });
        });
        groups.push(g);
      } else if (node.tagName === 'OPTION') {
        groups.push({ label: null, items: [{ value: node.value, text: node.textContent }] });
      }
    });
    return groups;
  }

  window.enhancePresetSelect = function (selectId, opts) {
    // Desktop's native <select><optgroup> already renders as a clear,
    // properly-indented list (that part was never broken) — only
    // mobile/tablet-width native picker popups mash group headers and
    // options together, so only THOSE get the custom picker. Leave desktop
    // completely untouched.
    if (window.innerWidth > 900) return;
    injectStyle();
    var sel = document.getElementById(selectId);
    if (!sel || sel._pickerEnhanced) return;
    sel._pickerEnhanced = true;
    sel.style.display = 'none';

    var trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'preset-picker-trigger';
    trigger.style.cssText = sel.style.cssText + ';cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:8px';
    trigger.innerHTML = '<span class="ppt-label"></span><i class="fa-solid fa-chevron-down" style="color:#94a3b8;font-size:.78rem;flex:none"></i>';
    sel.parentNode.insertBefore(trigger, sel.nextSibling);

    function refreshLabel() {
      var opt = sel.options[sel.selectedIndex];
      trigger.querySelector('.ppt-label').textContent = opt ? opt.textContent : '';
    }
    refreshLabel();
    sel.addEventListener('change', refreshLabel);

    function open() {
      var groups = buildGroups(sel);
      var overlay = document.createElement('div');
      overlay.className = 'preset-picker-overlay';
      var sheet = document.createElement('div');
      sheet.className = 'preset-picker-sheet';
      sheet.innerHTML =
        '<div class="preset-picker-head">' +
          '<div class="pph-row"><h3>' + escapeHtml((opts && opts.title) || 'Select') + '</h3>' +
          '<button type="button" class="preset-picker-x" aria-label="Close">&times;</button></div>' +
          '<input type="text" class="preset-picker-search" placeholder="Search karein…">' +
        '</div>' +
        '<div class="preset-picker-list"></div>';
      overlay.appendChild(sheet);
      document.body.appendChild(overlay);
      var prevOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';

      var listEl = sheet.querySelector('.preset-picker-list');
      var searchEl = sheet.querySelector('.preset-picker-search');

      function render(filter) {
        var f = (filter || '').trim().toLowerCase();
        var html = '';
        groups.forEach(function (g) {
          var items = g.items.filter(function (it) { return !f || it.text.toLowerCase().indexOf(f) !== -1; });
          if (!items.length) return;
          if (g.label) html += '<div class="preset-picker-group">' + escapeHtml(g.label) + '</div>';
          items.forEach(function (it) {
            var active = it.value === sel.value && it.value !== '';
            html += '<div class="preset-picker-item' + (active ? ' active' : '') + '" data-value="' + escapeHtml(it.value) + '">' +
              '<span>' + escapeHtml(it.text) + '</span>' +
              (active ? '<i class="fa-solid fa-check"></i>' : '') + '</div>';
          });
        });
        listEl.innerHTML = html || '<div class="preset-picker-empty">Koi match nahi mila</div>';
        listEl.querySelectorAll('.preset-picker-item').forEach(function (row) {
          row.addEventListener('click', function () {
            sel.value = row.getAttribute('data-value');
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            refreshLabel();
            close();
          });
        });
      }
      render('');
      searchEl.addEventListener('input', function () { render(searchEl.value); });

      function close() {
        document.body.removeChild(overlay);
        document.body.style.overflow = prevOverflow;
      }
      overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
      sheet.querySelector('.preset-picker-x').addEventListener('click', close);
      setTimeout(function () { searchEl.focus(); }, 50);
    }

    trigger.addEventListener('click', open);
  };
})();
