/**
 * dynamic-template.js
 * TopSarkariJobs — Dynamic Job Poster Template System
 * Generates category-specific poster HTML from job data
 */

(function (window) {
  'use strict';

  /* ════════════════════════════════════════
     1. CATEGORY DETECTION
  ════════════════════════════════════════ */
  const CATEGORY_MAP = {
    // Jobs
    'latest-notifications': { theme: 'jobs',    label: '📋 Latest Jobs',        icon: '💼' },
    'police-defence':       { theme: 'police',   label: '🛡️ Police / Defence',   icon: '🛡️' },
    'railway-jobs':         { theme: 'railway',  label: '🚂 Railway Jobs',        icon: '🚂' },
    'bank-jobs':            { theme: 'bank',     label: '🏦 Bank Jobs',            icon: '🏦' },
    'teaching-faculty':     { theme: 'jobs',     label: '🎓 Teaching / Faculty',  icon: '🎓' },
    'medical-hospital':     { theme: 'result',   label: '🏥 Medical / Hospital',  icon: '🏥' },
    'iti':                  { theme: 'jobs',     label: '🔧 ITI / Tech',           icon: '🔧' },
    '12th-pass':            { theme: 'jobs',     label: '📚 12th Pass',            icon: '📚' },
    '10th-pass':            { theme: 'jobs',     label: '📖 10th Pass',            icon: '📖' },
    'any-graduate':         { theme: 'jobs',     label: '🎓 Graduate',             icon: '🎓' },
    'b-tech-be':            { theme: 'jobs',     label: '⚙️ B.Tech / B.E.',        icon: '⚙️' },
    'diploma':              { theme: 'jobs',     label: '📄 Diploma',              icon: '📄' },
    // Result
    'result':               { theme: 'result',   label: '✅ Result',               icon: '✅' },
    // Admit Card
    'admit-card':           { theme: 'admit',    label: '🎫 Admit Card',           icon: '🎫' },
    // Scholarship
    'scholarship':          { theme: 'scholar',  label: '🏅 Scholarship',          icon: '🏅' },
    // Yojana
    'yojana':               { theme: 'yojana',   label: '🤝 Yojana',              icon: '🤝' },
    // Army specific
    'army':                 { theme: 'army',     label: '⭐ Army Jobs',            icon: '⭐' },
  };

  const THEME_CONFIG = {
    jobs:    { from: '#1a3a6b', to: '#0d6efd', accent: '#ffc107' },
    result:  { from: '#0a4d2e', to: '#198754', accent: '#a8ff78' },
    admit:   { from: '#3a0a6e', to: '#7c3aed', accent: '#f5a623' },
    scholar: { from: '#7a3900', to: '#fd7e14', accent: '#fff176' },
    yojana:  { from: '#6b0a0a', to: '#dc3545', accent: '#ffc107' },
    police:  { from: '#1a2e4a', to: '#2563eb', accent: '#f59e0b' },
    railway: { from: '#003d00', to: '#16a34a', accent: '#facc15' },
    army:    { from: '#3d2a00', to: '#92400e', accent: '#86efac' },
    bank:    { from: '#0c2d6e', to: '#1d4ed8', accent: '#fbbf24' },
  };

  function detectCategory(jobData, slug) {
    // Check slug for category hints
    const s = (slug || '').toLowerCase();
    for (const [key, cfg] of Object.entries(CATEGORY_MAP)) {
      if (s.includes(key.replace(/-/g, '-'))) return cfg;
    }
    // Check job category field
    const cat = ((jobData.category || jobData.basic_details?.category || '')).toLowerCase();
    const catWords = cat.replace(/_/g, '-');
    for (const [key, cfg] of Object.entries(CATEGORY_MAP)) {
      if (catWords.includes(key)) return cfg;
    }
    // Check job title for hints
    const title = (jobData.basic_details?.job_title || '').toLowerCase();
    if (title.includes('police') || title.includes('constable') || title.includes('crpf') || title.includes('cisf') || title.includes('bsf') || title.includes('itbp') || title.includes('ssb')) return CATEGORY_MAP['police-defence'];
    if (title.includes('railway') || title.includes('rrb') || title.includes('loco')) return CATEGORY_MAP['railway-jobs'];
    if (title.includes('army') || title.includes('military') || title.includes('navy') || title.includes('air force') || title.includes('defence')) return CATEGORY_MAP['army'];
    if (title.includes('bank') || title.includes('sbi') || title.includes('rbi') || title.includes('nabard') || title.includes('ibps')) return CATEGORY_MAP['bank-jobs'];
    if (title.includes('result')) return CATEGORY_MAP['result'];
    if (title.includes('admit')) return CATEGORY_MAP['admit-card'];
    if (title.includes('scholarship')) return CATEGORY_MAP['scholarship'];
    if (title.includes('yojana')) return CATEGORY_MAP['yojana'];
    return CATEGORY_MAP['latest-notifications'];
  }

  /* ════════════════════════════════════════
     2. DATA EXTRACTION HELPERS
  ════════════════════════════════════════ */
  function extractField(jobData, ...paths) {
    for (const path of paths) {
      const keys = path.split('.');
      let val = jobData;
      for (const k of keys) { val = val?.[k]; if (!val) break; }
      if (val && typeof val === 'string' && val.trim()) return val.trim();
    }
    return null;
  }

  function extractDates(jobData) {
    const id = jobData.important_dates || {};
    const dates = [];

    const addDate = (label, val) => {
      if (val && typeof val === 'string' && val.trim() && val.trim().toLowerCase() !== 'n/a') {
        dates.push({ label, val: val.trim() });
      }
    };

    addDate('आवेदन प्रारंभ', id.application_start_date || id.starting_date_for_apply_online);
    addDate('अंतिम तिथि', id.last_date_to_apply || id.last_date_for_apply_online || id.last_date);
    addDate('एडमिट कार्ड', id.admit_card_date || id.admit_card);
    addDate('परीक्षा तिथि', id.exam_date);
    addDate('रिजल्ट', id.result_date);

    // Parse raw dates string if structured fields empty
    if (dates.length === 0 && id.raw) {
      const rawStr = id.raw;
      const patterns = [
        { re: /Starting Date[^:]*:\s*([^\n\r|]+)/i, label: 'आवेदन प्रारंभ' },
        { re: /Last Date[^:]*:\s*([^\n\r|]+)/i,     label: 'अंतिम तिथि' },
        { re: /Admit Card[^:]*:\s*([^\n\r|]+)/i,    label: 'एडमिट कार्ड' },
        { re: /Exam Date[^:]*:\s*([^\n\r|]+)/i,     label: 'परीक्षा तिथि' },
      ];
      patterns.forEach(({ re, label }) => {
        const m = rawStr.match(re);
        if (m) dates.push({ label, val: m[1].trim().substring(0, 30) });
      });
    }

    return dates.slice(0, 4);
  }

  function extractVacancy(jobData) {
    return extractField(jobData,
      'basic_details.total_vacancies',
      'basic_details.total_posts',
      'basic_details.post_name'
    );
  }

  function extractSalary(jobData) {
    return extractField(jobData,
      'salary_details.pay_scale',
      'salary_details.details',
      'basic_details.salary'
    );
  }

  function extractQualification(jobData) {
    const q = extractField(jobData,
      'qualification.education_qualification',
      'qualification.details',
      'basic_details.qualification'
    );
    if (!q) return null;
    return q.length > 60 ? q.substring(0, 57) + '…' : q;
  }

  function extractAge(jobData) {
    return extractField(jobData,
      'age_limit.age_details',
      'age_limit.details',
      'basic_details.age_limit'
    );
  }

  function extractLastDate(jobData) {
    return extractField(jobData,
      'important_dates.last_date_to_apply',
      'important_dates.last_date_for_apply_online',
      'important_dates.last_date'
    );
  }

  function extractApplyMode(jobData) {
    return extractField(jobData,
      'basic_details.application_mode',
      'basic_details.apply_mode'
    );
  }

  function isUrgent(lastDateStr) {
    if (!lastDateStr) return false;
    try {
      // Try parsing dd-mm-yyyy or dd/mm/yyyy
      const parts = lastDateStr.match(/(\d{1,2})[-\/](\d{1,2})[-\/](\d{2,4})/);
      if (!parts) return false;
      const d = new Date(+parts[3], +parts[2] - 1, +parts[1]);
      const diff = (d - Date.now()) / 86400000;
      return diff >= 0 && diff <= 7;
    } catch { return false; }
  }

  /* ════════════════════════════════════════
     3. QR CODE GENERATOR (tiny, pure JS)
  ════════════════════════════════════════ */
  function generateSimpleQR(url, size) {
    // Build QR as a colored box pattern using canvas (simplified visual)
    const canvas = document.createElement('canvas');
    canvas.width = size; canvas.height = size;
    const ctx = canvas.getContext('2d');
    // White background
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, size, size);
    // Draw finder pattern corners (just as visual indicator)
    ctx.fillStyle = '#000';
    const cell = Math.floor(size / 21);
    // Top-left finder
    ctx.fillRect(0,0,7*cell,7*cell);
    ctx.fillStyle = '#fff';
    ctx.fillRect(cell,cell,5*cell,5*cell);
    ctx.fillStyle = '#000';
    ctx.fillRect(2*cell,2*cell,3*cell,3*cell);
    // Top-right finder
    ctx.fillStyle = '#000';
    ctx.fillRect(14*cell,0,7*cell,7*cell);
    ctx.fillStyle = '#fff';
    ctx.fillRect(15*cell,cell,5*cell,5*cell);
    ctx.fillStyle = '#000';
    ctx.fillRect(16*cell,2*cell,3*cell,3*cell);
    // Bottom-left finder
    ctx.fillStyle = '#000';
    ctx.fillRect(0,14*cell,7*cell,7*cell);
    ctx.fillStyle = '#fff';
    ctx.fillRect(cell,15*cell,5*cell,5*cell);
    ctx.fillStyle = '#000';
    ctx.fillRect(2*cell,16*cell,3*cell,3*cell);
    // Timing patterns
    for (let i = 8; i <= 12; i++) {
      if ((i % 2) === 0) {
        ctx.fillStyle = '#000';
        ctx.fillRect(i*cell,6*cell,cell,cell);
        ctx.fillRect(6*cell,i*cell,cell,cell);
      }
    }
    // Data area (random-ish using URL hash for pseudo-uniqueness)
    let h = 0;
    for (const c of url) h = ((h << 5) - h + c.charCodeAt(0)) | 0;
    for (let r = 8; r <= 20; r++) {
      for (let c = 8; c <= 20; c++) {
        if (r <= 14 && c <= 6) continue; // Skip bottom-left finder
        if ((h ^ (r * 37 + c * 13)) & 1) {
          ctx.fillStyle = '#000';
          ctx.fillRect(c * cell, r * cell, cell, cell);
        }
      }
    }
    // Format info strip
    for (let i = 0; i <= 20; i++) {
      if (i === 6) continue;
      const shade = ((h + i) % 3 === 0) ? '#000' : 'transparent';
      ctx.fillStyle = shade;
      ctx.fillRect(i * cell, 6 * cell, cell, cell);
    }
    return canvas;
  }

  /* ════════════════════════════════════════
     4. HTML BUILDER
  ════════════════════════════════════════ */
  function buildPosterHTML(jobData, slug, pageUrl) {
    const catInfo = detectCategory(jobData, slug);
    const theme   = THEME_CONFIG[catInfo.theme] || THEME_CONFIG.jobs;
    const accent  = theme.accent;

    // Extract key data
    const title     = extractField(jobData, 'basic_details.job_title') || 'Sarkari Job 2026';
    const org       = extractField(jobData, 'basic_details.organization_name', 'basic_details.department') || '';
    const postName  = extractField(jobData, 'basic_details.post_name') || '';
    const vacancy   = extractVacancy(jobData) || '';
    const salary    = extractSalary(jobData) || '';
    const qual      = extractQualification(jobData) || '';
    const age       = extractAge(jobData) || '';
    const applyMode = extractApplyMode(jobData) || '';
    const lastDate  = extractLastDate(jobData) || '';
    const dates     = extractDates(jobData);
    const officialLink = (jobData.important_links?.click_here?.[0]) || '#';
    const urgent    = isUrgent(lastDate);

    // Clean title for display
    const dispTitle = title.replace(/Recruitment 2026.*$/i, '').replace(/\s+/g, ' ').trim();
    const year = title.match(/20\d{2}/)?.at(0) || '2026';

    const bgGradient = `linear-gradient(135deg, ${theme.from} 0%, ${theme.to} 100%)`;

    // Build pills
    const pills = [];
    if (org) pills.push({ icon: '🏛️', label: 'संगठन', val: org.split('(')[0].trim().substring(0, 25) });
    if (postName && postName !== 'Total') pills.push({ icon: '💼', label: 'पद', val: postName.substring(0, 30) });
    if (qual) pills.push({ icon: '🎓', label: 'योग्यता', val: qual });
    if (age) pills.push({ icon: '👤', label: 'आयु', val: age.substring(0, 30) });
    if (salary) pills.push({ icon: '💰', label: 'वेतन', val: salary.substring(0, 35) });
    if (applyMode) pills.push({ icon: '📝', label: 'आवेदन', val: applyMode });

    const pillsHTML = pills.slice(0, 4).map(p => `
      <div class="tsj-pill">
        <span class="tsj-pill__icon">${p.icon}</span>
        <div>
          <div class="tsj-pill__label">${p.label}</div>
          <div class="tsj-pill__val">${escHtml(p.val)}</div>
        </div>
      </div>`).join('');

    // Dates
    const datesHTML = dates.length ? dates.map(d => `
      <div class="tsj-date-row">
        <span class="tsj-date-row__icon">📅</span>
        <div class="tsj-date-row__info">
          <div class="tsj-date-row__label">${escHtml(d.label)}</div>
          <div class="tsj-date-row__val ${urgent && d.label.includes('अंतिम') ? 'urgent' : ''}">${escHtml(d.val)}</div>
        </div>
      </div>`).join('') : '';

    // Benefits (generic gov job perks)
    const benefits = ['सरकारी नियम भत्ते', 'नौकरी सुरक्षा', 'पेंशन लाभ', 'चिकित्सा सुविधा'];
    const benefitsHTML = benefits.map(b => `<div class="tsj-benefit-item">${escHtml(b)}</div>`).join('');

    // Info grid items
    const infoItems = [];
    if (applyMode) infoItems.push({ icon: '📝', label: 'आवेदन:', val: applyMode });
    if (lastDate) infoItems.push({ icon: '⏰', label: 'अंतिम तिथि:', val: lastDate });
    if (salary) infoItems.push({ icon: '💵', label: 'वेतन:', val: salary.substring(0, 40) });
    const infoHTML = infoItems.map(i => `
      <div class="tsj-info-item">
        <span class="tsj-info-item__icon">${i.icon}</span>
        <span class="tsj-info-item__label">${escHtml(i.label)}</span>
        <span class="tsj-info-item__val">${escHtml(i.val)}</span>
      </div>`).join('');

    // Vacancy display
    const vacancyNum = vacancy ? (isNaN(+vacancy.replace(/,/g,'')) ? vacancy : (+vacancy.replace(/,/g,'')).toLocaleString('en-IN')) : '—';
    const showVacancy = vacancy && vacancy !== '0';

    return `
<div class="tsj-poster" style="--accent:${accent}; --poster-bg:${bgGradient};" role="img" aria-label="${escAttr(title)}">

  <!-- Header Strip -->
  <div class="tsj-poster__header">
    <div class="tsj-poster__brand">
      <div class="tsj-poster__brand-icon">🏛️</div>
      <div>
        <div class="tsj-poster__brand-name">Top<span>Sarkari</span>Jobs.com</div>
        <div class="tsj-poster__brand-sub">Sarkari Jobs • Results • Admit Card • Yojana</div>
      </div>
    </div>
    <div class="tsj-poster__badge">
      🔔 Latest ${year}
    </div>
  </div>

  <!-- Hero Body -->
  <div class="tsj-poster__body" style="background:${bgGradient};">

    <!-- Left: Title + Pills -->
    <div class="tsj-poster__left">
      <div class="tsj-poster__category-tag">${catInfo.label}</div>
      ${org ? `<div class="tsj-poster__org">${escHtml(org.substring(0, 50))}</div>` : ''}
      <h1 class="tsj-poster__title">${escHtml(dispTitle)}</h1>
      ${postName && postName !== 'Total' ? `<div class="tsj-poster__subtitle">${escHtml(postName)} — Recruitment ${year}</div>` : ''}
      ${pillsHTML ? `<div class="tsj-poster__pills">${pillsHTML}</div>` : ''}
    </div>

    <!-- Right: Vacancy Circle + Dates -->
    <div class="tsj-poster__right">
      ${showVacancy ? `
      <div class="tsj-vacancy-circle">
        <div class="tsj-vacancy-circle__pre">कुल पद</div>
        <div class="tsj-vacancy-circle__num">${escHtml(vacancyNum)}</div>
        <div class="tsj-vacancy-circle__post">${escHtml(postName && postName !== 'Total' ? postName.substring(0,18) : 'पद')}</div>
        <div class="tsj-vacancy-circle__cta">जल्दी करें!</div>
      </div>` : ''}

      ${datesHTML ? `
      <div class="tsj-dates-card">
        <div class="tsj-dates-card__title">⏳ महत्वपूर्ण तिथियां</div>
        ${datesHTML}
      </div>` : ''}
    </div>

  </div><!-- /body -->

  <!-- Info Grid -->
  ${infoHTML ? `<div class="tsj-poster__info-grid">${infoHTML}</div>` : ''}

  <!-- Benefits -->
  <div class="tsj-poster__benefits">
    ${benefitsHTML}
  </div>

  <!-- CTA Strip -->
  <div class="tsj-poster__cta-strip">
    <div class="tsj-cta-actions">
      <a href="${escAttr(officialLink !== '#' ? officialLink : pageUrl)}" target="_blank" rel="noopener" class="tsj-cta-btn tsj-cta-btn--primary">
        📝 ऑनलाइन आवेदन
      </a>
      <button class="tsj-cta-btn tsj-cta-btn--ghost" onclick="TSJPoster.share('${escAttr(pageUrl)}','${escAttr(title)}')" title="Share">
        📤 Share
      </button>
      <button class="tsj-cta-btn tsj-cta-btn--ghost" onclick="TSJPoster.downloadPoster()" title="Download Poster">
        ⬇️ Download
      </button>
    </div>
    <div class="tsj-qr-wrap">
      <div class="tsj-qr-box" id="tsj-qr-canvas"></div>
      <div class="tsj-qr-label">Scan Me</div>
    </div>
  </div>

</div>`;
  }

  /* ════════════════════════════════════════
     5. UTILITIES
  ════════════════════════════════════════ */
  function escHtml(str) {
    return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function escAttr(str) {
    return String(str || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  /* ════════════════════════════════════════
     6. PUBLIC API
  ════════════════════════════════════════ */
  window.TSJPosterTemplate = {
    build: buildPosterHTML,
    detect: detectCategory,

    initQR(url) {
      try {
        const container = document.getElementById('tsj-qr-canvas');
        if (!container) return;
        const canvas = generateSimpleQR(url, 44);
        container.innerHTML = '';
        container.appendChild(canvas);
      } catch (e) {}
    },

    share(url, title) {
      if (navigator.share) {
        navigator.share({ title, text: title + ' — TopSarkariJobs', url })
          .catch(() => fallbackCopy(url));
      } else {
        fallbackCopy(url);
      }
    },

    downloadPoster() {
      const poster = document.querySelector('.tsj-poster');
      if (!poster) return;
      // Use html2canvas if available
      if (window.html2canvas) {
        window.html2canvas(poster, { scale: 2, useCORS: true }).then(canvas => {
          const a = document.createElement('a');
          a.download = 'job-poster.png';
          a.href = canvas.toDataURL('image/png');
          a.click();
        });
      } else {
        alert('Download: Right-click the poster and select "Save image" or use the Print option.');
      }
    }
  };

  function fallbackCopy(url) {
    try {
      navigator.clipboard.writeText(url).then(() => alert('Link copied!'));
    } catch {
      const ta = document.createElement('textarea');
      ta.value = url;
      document.body.appendChild(ta);
      ta.select(); document.execCommand('copy');
      document.body.removeChild(ta);
      alert('Link copied!');
    }
  }

})(window);
