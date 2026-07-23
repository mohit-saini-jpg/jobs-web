/* "Form Filling Request" (CSC Partner Team) lead-capture widget.
   Mounted into #tsj-job-form-widget on every job detail page (see
   JOB_FORM_WIDGET_HTML in generate_all.py). Job title + page URL are read
   from the page itself at runtime — nothing job-specific is rendered
   server-side, so this file is identical (and fully cacheable) across
   every job page. Submits to /api/submit-lead, which inserts into
   Supabase and fires an admin Telegram alert server-side. */
(function () {
  var HARYANA_DISTRICTS = [
    'Ambala', 'Bhiwani', 'Charkhi Dadri', 'Faridabad', 'Fatehabad', 'Gurugram',
    'Hisar', 'Jhajjar', 'Jind', 'Kaithal', 'Karnal', 'Kurukshetra',
    'Mahendragarh', 'Nuh', 'Palwal', 'Panchkula', 'Panipat', 'Rewari',
    'Rohtak', 'Sirsa', 'Sonipat', 'Yamunanagar', 'Other / Outside Haryana'
  ];

  function getJobTitle() {
    var h1 = document.querySelector('h1.detail-h1') || document.querySelector('h1');
    if (h1 && h1.textContent.trim()) return h1.textContent.trim();
    return (document.title || '').split(/[–—|]/)[0].trim() || 'Government Job';
  }

  function getPageUrl() {
    var canon = document.querySelector('link[rel="canonical"]');
    return (canon && canon.href) || location.href;
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function render(mount) {
    var jobTitle = getJobTitle();
    var pageUrl = getPageUrl();

    mount.innerHTML =
      '<div class="jfw-box">' +
      '<div class="jfw-head">🏠 घर बैठे फॉर्म भरवाएं (CSC Partner Team)</div>' +
      '<div class="jfw-sub">ऑफ़िशियल CSC टीम से अपना फ़ॉर्म 100% सही भरवाएं</div>' +
      '<div class="jfw-job">आप जिस जॉब को देख रहे हैं:<b>' + escapeHtml(jobTitle) + '</b></div>' +
      '<form id="jfwForm" novalidate>' +
      '<div class="jfw-field"><label>पूरा नाम</label><input type="text" id="jfwName" placeholder="अपना पूरा नाम लिखें" required autocomplete="name"></div>' +
      '<div class="jfw-field"><label>WhatsApp नंबर</label><input type="tel" id="jfwPhone" placeholder="10 अंकों का मोबाइल नंबर" required maxlength="10" inputmode="numeric" autocomplete="tel"></div>' +
      '<div class="jfw-field"><label>ज़िला (District)</label><select id="jfwDistrict" required>' +
      '<option value="" disabled selected>ज़िला चुनें</option>' +
      HARYANA_DISTRICTS.map(function (d) { return '<option value="' + escapeHtml(d) + '">' + escapeHtml(d) + '</option>'; }).join('') +
      '</select></div>' +
      '<button type="submit" class="jfw-btn" id="jfwSubmitBtn">📩 Request Form Filling (WhatsApp)</button>' +
      '<div class="jfw-note">🔒 आपकी जानकारी सुरक्षित है — सिर्फ़ CSC Partner Team आपसे संपर्क करेगी</div>' +
      '<div class="jfw-msg" id="jfwMsg"></div>' +
      '</form>' +
      '</div>';

    var form = mount.querySelector('#jfwForm');
    var msgEl = mount.querySelector('#jfwMsg');
    var btn = mount.querySelector('#jfwSubmitBtn');

    function showMsg(text, kind) {
      msgEl.textContent = text;
      msgEl.className = 'jfw-msg show ' + kind;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = mount.querySelector('#jfwName').value.trim();
      var phone = mount.querySelector('#jfwPhone').value.trim();
      var district = mount.querySelector('#jfwDistrict').value;

      if (!name) { showMsg('कृपया अपना नाम लिखें।', 'err'); return; }
      if (!/^[6-9][0-9]{9}$/.test(phone)) { showMsg('कृपया सही 10 अंकों का मोबाइल नंबर डालें।', 'err'); return; }
      if (!district) { showMsg('कृपया अपना ज़िला चुनें।', 'err'); return; }

      btn.disabled = true;
      btn.textContent = 'भेजा जा रहा है...';
      msgEl.className = 'jfw-msg';

      fetch('/api/submit-lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          whatsapp: phone,
          district: district,
          job_title: jobTitle,
          page_url: pageUrl
        })
      })
        .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
        .then(function (r) {
          if (!r.ok) throw new Error((r.data && r.data.error) || 'submit failed');
          showMsg('✅ आपकी Request मिल गई! CSC Partner Team जल्द ही ' + phone + ' पर WhatsApp करेगी।', 'ok');
          form.reset();
          btn.textContent = '📩 Request Form Filling (WhatsApp)';
          btn.disabled = false;
        })
        .catch(function () {
          showMsg('कुछ गड़बड़ हो गई। Internet check करें और दोबारा try करें।', 'err');
          btn.textContent = '📩 Request Form Filling (WhatsApp)';
          btn.disabled = false;
        });
    });
  }

  function init() {
    var mount = document.getElementById('tsj-job-form-widget');
    if (!mount) return;
    render(mount);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
