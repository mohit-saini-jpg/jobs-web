/**
 * ============================================================
 *  TOP SARKARI JOBS — ADVANCED SHARE SYSTEM  v2.0
 *  File: advanced-share-system.js
 *  Drop this ONCE anywhere before </body> on job.html
 * ============================================================
 *
 *  WHAT THIS MODULE DOES:
 *  1. Generates fully dynamic WhatsApp share text (rich + encoded)
 *  2. Injects/updates all OG + Twitter meta tags per job
 *  3. Sets canonical + hreflang correctly for each slug
 *  4. Upgrades all 4 share buttons with UTM-tracked URLs
 *  5. Adds Copy-Link, Native-Share (mobile) buttons
 *  6. Handles OG image with 1200×630 fallback
 *  7. Exposes window.TSJ_Share for external calls
 *
 *  HOW TO INTEGRATE:
 *  - Save this file as /advanced-share-system.js
 *  - Add ONE line at bottom of job.html (before </body>):
 *      <script src="/advanced-share-system.js" defer></script>
 *  - The module hooks into the existing renderJobPage() flow automatically.
 *
 *  DATA CONTRACT (what it reads from job JSON row):
 *    row.name  / window.__tsjJobName       — Job title
 *    row.org                               — Organization name
 *    row.lastDate                          — Last date to apply
 *    row.totalVac                          — Total vacancies
 *    row.salary                            — Salary string (optional)
 *    row.qualification                     — Qualification string
 *    row.location / row.state              — Location
 *    row.department                        — Department (optional)
 *    row.image / row.ogImage               — Job image URL (optional)
 *    slug (from URL / sessionStorage)      — URL slug
 * ============================================================
 */

(function (win, doc) {
  'use strict';

  /* ─────────────────────────────────────────────
     SITE CONFIG — edit these if domain changes
  ─────────────────────────────────────────────── */
  var CFG = {
    siteUrl:       'https://www.topsarkarijobs.com',
    siteName:      'Top Sarkari Jobs',
    fallbackImage: 'https://www.topsarkarijobs.com/og-default.png', // 1200×630
    twitterHandle: '@TopSarkariJobs',
    hashtags:      'SarkariJob,LatestJobs,GovtJobs,SarkariResult',
    channel: {
      whatsapp:  'https://whatsapp.com/channel/0029Va…',  // ← update
      telegram:  'https://t.me/topsarkarijobs',           // ← update
    }
  };

  /* ─────────────────────────────────────────────
     UTILITIES
  ─────────────────────────────────────────────── */
  function safe(v) {
    return (v && typeof v === 'string') ? v.trim() : '';
  }

  /** Get current job slug from multiple sources */
  function getSlug() {
    var slug = '';
    try { slug = sessionStorage.getItem('__tsj_slug') || ''; } catch (_) {}
    if (!slug) {
      var m = win.location.pathname.match(/\/jobs\/([^\/]+)\/?$/);
      if (m) slug = decodeURIComponent(m[1]);
    }
    if (!slug) {
      try { slug = new URLSearchParams(win.location.search).get('slug') || ''; } catch (_) {}
    }
    return slug;
  }

  /** Build canonical job URL */
  function canonUrl(slug) {
    return CFG.siteUrl + '/jobs/' + encodeURIComponent(slug) + '/';
  }

  /** Append UTM params to a URL */
  function utm(baseUrl, source, medium) {
    medium = medium || 'social';
    var sep = baseUrl.indexOf('?') > -1 ? '&' : '?';
    return baseUrl + sep + 'utm_source=' + source + '&utm_medium=' + medium + '&utm_campaign=job_share';
  }

  /** setAttribute helper */
  function setAttr(id, attr, val) {
    var el = doc.getElementById(id);
    if (el) el.setAttribute(attr, val);
  }
  function setContent(id, val) { setAttr(id, 'content', val); }

  /** Truncate text to maxLen, respecting word boundaries */
  function trunc(str, maxLen) {
    str = safe(str);
    if (str.length <= maxLen) return str;
    return str.slice(0, maxLen - 1).replace(/\s+\S*$/, '') + '…';
  }

  /**
   * Build SEO-optimized meta description (unique per job, 150-300 chars).
   * Never returns duplicate content across jobs.
   */
  function buildMetaDesc(data) {
    var title  = safe(data.title);
    var org    = safe(data.org)    || 'Government Organisation';
    var qual   = safe(data.qual)   || '';
    var vacStr = data.vac          ? data.vac + ' ' + (parseInt(data.vac) === 1 ? 'vacancy' : 'vacancies') + '. ' : '';
    var lastDt = safe(data.lastDate) ? 'Last date: ' + data.lastDate + '. ' : '';
    var loc    = safe(data.location) ? 'Location: ' + data.location + '. ' : '';
    var salStr = safe(data.salary)   ? 'Pay Scale: ' + trunc(data.salary, 50) + '. ' : '';
    var qualStr = qual               ? 'Qualification: ' + trunc(qual, 60) + '. ' : '';

    var desc = title + ' – ' + org + '. ' + vacStr + qualStr + lastDt + loc + salStr +
      'Apply Online on ' + CFG.siteName + '. Latest Govt Jobs 2026.';

    // Ensure uniqueness — title is included so each job description is different
    if (desc.length < 150) {
      desc += ' Check salary, admit card, syllabus and direct official apply link.';
    }
    return trunc(desc, 300);
  }

  /**
   * Build OG / Twitter title — SEO keyword-rich, unique per job
   * Format: {Job Title} – Apply Online | Top Sarkari Jobs
   */
  function buildOgTitle(title) {
    var t = safe(title);
    var suffix = ' – Apply Online | ' + CFG.siteName;
    // Keep total under 70 chars for Twitter; OG can be longer
    if (t.length + suffix.length > 95) {
      t = trunc(t, 95 - suffix.length);
    }
    return t + suffix;
  }

  /**
   * Determine OG image URL.
   * Priority: job-specific image → fallback 1200×630 default.
   */
  function resolveOgImage(data) {
    var img = safe(data.image) || safe(data.ogImage);
    if (img) {
      // Ensure absolute URL
      if (img.indexOf('http') !== 0) img = CFG.siteUrl + (img[0] === '/' ? '' : '/') + img;
      return img;
    }
    return CFG.fallbackImage;
  }

  /* ─────────────────────────────────────────────
     1. WHATSAPP SHARE TEXT GENERATOR
  ─────────────────────────────────────────────── */

  /**
   * Generates formatted WhatsApp share text.
   * Returns { plain: '...', encoded: '...' }
   */
  function buildWhatsAppText(data, shareUrl) {
    var lines = [];

    lines.push('🔥 *' + safe(data.title) + '*');
    lines.push('');

    if (data.org)        lines.push('🏢 *Organisation:* ' + safe(data.org));
    if (data.department) lines.push('📂 *Department:* '   + safe(data.department));
    if (data.location)   lines.push('📍 *Location:* '     + safe(data.location));
    if (data.vac)        lines.push('📋 *Total Posts:* '  + safe(data.vac));
    if (data.qual)       lines.push('🎓 *Qualification:* '+ trunc(data.qual, 80));
    if (data.salary)     lines.push('💰 *Salary:* '       + trunc(data.salary, 60));
    if (data.lastDate)   lines.push('📅 *Last Date:* '    + safe(data.lastDate));

    lines.push('');
    lines.push('👉 *Apply Now:*');
    lines.push(shareUrl);
    lines.push('');
    lines.push('#' + CFG.hashtags.replace(/,/g, ' #'));

    var plain   = lines.join('\n');
    var encoded = lines.join('%0A').replace(/ /g, '%20').replace(/\*/g, '*');

    return { plain: plain, encoded: encoded };
  }

  /* ─────────────────────────────────────────────
     2. META TAG INJECTION
  ─────────────────────────────────────────────── */

  /**
   * Injects / updates all Open Graph + Twitter Card tags.
   * Call this once job data is resolved.
   */
  function injectShareMeta(data) {
    var slug = data.slug || getSlug();
    if (!slug) return;

    var canon   = canonUrl(slug);
    var ogTitle = buildOgTitle(data.title);
    var ogDesc  = buildMetaDesc(data);
    var ogImg   = resolveOgImage(data);

    /* ── Page <title> ── */
    doc.title = ogTitle;

    /* ── Meta description ── */
    var mdEl = doc.getElementById('metaDesc');
    if (mdEl) mdEl.setAttribute('content', ogDesc);

    /* ── Canonical ── */
    var canEl = doc.getElementById('canonicalTag');
    if (canEl) canEl.href = canon;

    /* ── Hreflang ── */
    ['en', 'en-IN', 'x-default'].forEach(function (lang) {
      var el = doc.querySelector('link[hreflang="' + lang + '"]');
      if (!el) {
        el = doc.createElement('link');
        el.rel = 'alternate';
        el.setAttribute('hreflang', lang);
        doc.head.appendChild(el);
      }
      el.href = canon;
    });

    /* ── Open Graph ── */
    setContent('ogTitle', ogTitle);
    setContent('ogDesc',  ogDesc);
    setContent('ogUrl',   canon);

    // OG Image — update the static <meta> already in head
    var ogImgEl = doc.querySelector('meta[property="og:image"]');
    if (ogImgEl) ogImgEl.setAttribute('content', ogImg);

    // Image dimensions — 1200×630 is ideal
    var ogImgW = doc.querySelector('meta[property="og:image:width"]');
    var ogImgH = doc.querySelector('meta[property="og:image:height"]');
    if (ogImgW) ogImgW.setAttribute('content', '1200');
    if (ogImgH) ogImgH.setAttribute('content', '630');

    /* ── Twitter Card ── */
    setContent('twTitle', ogTitle);
    setContent('twDesc',  ogDesc);

    // twitter:image — add if missing
    var twImg = doc.querySelector('meta[name="twitter:image"]');
    if (!twImg) {
      twImg = doc.createElement('meta');
      twImg.setAttribute('name', 'twitter:image');
      doc.head.appendChild(twImg);
    }
    twImg.setAttribute('content', ogImg);

    // twitter:site
    var twSite = doc.querySelector('meta[name="twitter:site"]');
    if (!twSite) {
      twSite = doc.createElement('meta');
      twSite.setAttribute('name', 'twitter:site');
      twSite.setAttribute('content', CFG.twitterHandle);
      doc.head.appendChild(twSite);
    }
  }

  /* ─────────────────────────────────────────────
     3. SHARE BUTTON UPDATER
  ─────────────────────────────────────────────── */

  /**
   * Updates the 4 existing share buttons (#shFb, #shTw, #shWa, #shTg)
   * with rich UTM-tracked URLs. Also upgrades the copy button and
   * injects a Native Share button if supported.
   */
  function updateShareButtons(data) {
    var slug = data.slug || getSlug();
    if (!slug) return;

    var baseUrl = canonUrl(slug);
    var waText  = buildWhatsAppText(data, utm(baseUrl, 'whatsapp'));
    var tgText  = buildWhatsAppText(data, utm(baseUrl, 'telegram'));

    /* ── WhatsApp: rich formatted text ── */
    var waEl = doc.getElementById('shWa');
    if (waEl) {
      waEl.href = 'https://wa.me/?text=' + waText.encoded;
      waEl.setAttribute('data-action', 'whatsapp-share');
      waEl.setAttribute('title', 'Share on WhatsApp');
    }

    /* ── Telegram: title + URL ── */
    var tgEl = doc.getElementById('shTg');
    if (tgEl) {
      var tgTitle = encodeURIComponent(safe(data.title) + ' | ' + CFG.siteName);
      tgEl.href = 'https://t.me/share/url?url=' + encodeURIComponent(utm(baseUrl, 'telegram')) + '&text=' + tgTitle;
    }

    /* ── Facebook ── */
    var fbEl = doc.getElementById('shFb');
    if (fbEl) {
      fbEl.href = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(utm(baseUrl, 'facebook'));
    }

    /* ── Twitter / X: title + hashtags + URL ── */
    var twEl = doc.getElementById('shTw');
    if (twEl) {
      var twText = encodeURIComponent(trunc(data.title, 80) + ' — Apply Now 👉');
      var twUrl  = encodeURIComponent(utm(baseUrl, 'twitter'));
      var twTags = encodeURIComponent(CFG.hashtags);
      twEl.href  = 'https://twitter.com/intent/tweet?text=' + twText + '&url=' + twUrl + '&hashtags=' + twTags;
    }

    /* ── Copy Link button — upgrade to UTM version ── */
    var cpEl = doc.querySelector('.sh-cp');
    if (cpEl) {
      cpEl.onclick = function () {
        var copyUrl = utm(baseUrl, 'copy');
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(copyUrl).then(function () {
            cpEl.innerHTML = '<i class="fa-solid fa-check"></i>';
            setTimeout(function () { cpEl.innerHTML = '<i class="fa-solid fa-copy"></i>'; }, 2000);
          });
        } else {
          // Fallback for older browsers
          var ta = doc.createElement('textarea');
          ta.value = copyUrl;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          doc.body.appendChild(ta);
          ta.select();
          doc.execCommand('copy');
          doc.body.removeChild(ta);
          alert('Link copied!');
        }
      };
    }

    /* ── Native Share button (mobile only) ── */
    if (navigator.share) {
      injectNativeShareButton(data, baseUrl);
    }

    /* ── WhatsApp text preview panel (optional, hidden by default) ── */
    injectWhatsAppPreview(waText.plain, waEl);
  }

  /* ─────────────────────────────────────────────
     NATIVE SHARE BUTTON INJECTOR (Mobile)
  ─────────────────────────────────────────────── */
  function injectNativeShareButton(data, baseUrl) {
    if (doc.getElementById('shNative')) return; // already injected
    var container = doc.querySelector('.jp-share-btns');
    if (!container) return;

    var btn = doc.createElement('button');
    btn.id        = 'shNative';
    btn.className = 'jp-share-btn sh-native';
    btn.title     = 'Share';
    btn.innerHTML = '<i class="fa-solid fa-share"></i>';
    btn.style.cssText = 'background:#0ea5e9;color:#fff;';

    btn.addEventListener('click', function () {
      navigator.share({
        title: trunc(data.title, 60) + ' | ' + CFG.siteName,
        text:  'Apply for ' + safe(data.title) + '. Last Date: ' + safe(data.lastDate),
        url:   utm(baseUrl, 'native-share')
      }).catch(function () { /* user cancelled — ignore */ });
    });

    container.appendChild(btn);
  }

  /* ─────────────────────────────────────────────
     WHATSAPP PREVIEW PANEL
  ─────────────────────────────────────────────── */
  function injectWhatsAppPreview(plainText, waAnchor) {
    if (!waAnchor) return;
    if (doc.getElementById('waPreviewPanel')) return;

    /* Inject styles once */
    if (!doc.getElementById('tsj-share-styles')) {
      var st = doc.createElement('style');
      st.id = 'tsj-share-styles';
      st.textContent = [
        '.wa-preview-wrap{position:relative;display:inline-block;}',
        '#waPreviewPanel{',
        '  display:none;position:absolute;bottom:46px;left:0;width:270px;z-index:9999;',
        '  background:#ecfdf5;border:1px solid #d1fae5;border-radius:10px;',
        '  padding:12px;font-size:.75rem;line-height:1.55;color:#065f46;',
        '  box-shadow:0 4px 16px rgba(0,0,0,.15);white-space:pre-wrap;word-break:break-word;',
        '}',
        '#waPreviewPanel::after{content:"";position:absolute;bottom:-8px;left:14px;',
        '  border-width:8px 8px 0;border-style:solid;border-color:#d1fae5 transparent transparent;}',
        '.wa-preview-close{position:absolute;top:6px;right:8px;cursor:pointer;',
        '  font-size:.85rem;color:#047857;font-weight:700;}',
        '.sh-native{background:#0ea5e9!important;}',
      ].join('');
      doc.head.appendChild(st);
    }

    /* Wrap the WA button */
    var wrap = doc.createElement('span');
    wrap.className = 'wa-preview-wrap';
    waAnchor.parentNode.insertBefore(wrap, waAnchor);
    wrap.appendChild(waAnchor);

    /* Build panel */
    var panel = doc.createElement('div');
    panel.id = 'waPreviewPanel';
    panel.innerHTML = '<span class="wa-preview-close" id="waPreviewClose">✕</span>' +
      '<strong style="display:block;margin-bottom:6px;font-size:.78rem;">WhatsApp Preview</strong>' +
      doc.createTextNode('').constructor.name; // just a dummy
    panel.childNodes[0]; // noop

    // Use textContent to safely set the message
    var msgNode = doc.createElement('div');
    msgNode.style.whiteSpace = 'pre-wrap';
    msgNode.textContent = plainText;
    panel.appendChild(msgNode);
    wrap.appendChild(panel);

    /* Toggle panel on long-press / right-click — not on main click */
    var pressTimer;
    waAnchor.addEventListener('mousedown', function () {
      pressTimer = setTimeout(function () {
        panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
      }, 600);
    });
    waAnchor.addEventListener('mouseup',   function () { clearTimeout(pressTimer); });
    waAnchor.addEventListener('mouseleave',function () { clearTimeout(pressTimer); });
    waAnchor.addEventListener('touchstart',function () {
      pressTimer = setTimeout(function () {
        panel.style.display = 'block';
      }, 600);
    }, { passive: true });
    waAnchor.addEventListener('touchend',  function () { clearTimeout(pressTimer); });

    doc.getElementById('waPreviewClose').addEventListener('click', function (e) {
      e.stopPropagation(); e.preventDefault();
      panel.style.display = 'none';
    });
  }

  /* ─────────────────────────────────────────────
     4. HOOK INTO EXISTING renderJobPage()
  ─────────────────────────────────────────────── */

  /**
   * Called by window.TSJ_Share.init(row, parsed, slug)
   * — which is triggered from job.html after job data is loaded.
   *
   * Also tries to auto-hook by intercepting when job renders
   * via the existing __tsjRawJob global.
   */
  function init(row, parsed, slug) {
    row    = row    || {};
    parsed = parsed || {};
    slug   = slug   || getSlug();

    /* Assemble normalised data object */
    var data = {
      slug:       slug,
      title:      safe(row.name)         || safe(win.__tsjJobName) || 'Sarkari Job',
      org:        safe(row.org)          || safe(parsed.org)       || '',
      department: safe(row.department)   || '',
      location:   safe(row.location)     || safe(row.state)        || safe(parsed.location) || 'India',
      vac:        safe(row.totalVac)     || safe(parsed.vac)       || '',
      qual:       safe(row.qualification)|| safe(parsed.qualification) || '',
      salary:     safe(row.salary)       || safe(parsed.salary)    || '',
      lastDate:   safe(row.lastDate)     || safe(parsed.lastDt)    || '',
      image:      safe(row.image)        || safe(row.ogImage)      || '',
    };

    injectShareMeta(data);
    updateShareButtons(data);
  }

  /* ─────────────────────────────────────────────
     5. AUTO-DETECT when __tsjRawJob is set
  ─────────────────────────────────────────────── */
  function tryAutoHook() {
    var raw = win.__tsjRawJob;
    if (!raw) return;

    var basics = (raw.basic_details || {});
    var imp    = (raw.important_dates || {});
    var sal    = (raw.salary_details  || {});
    var qual   = (raw.qualification   || {});

    var row = {
      name:          basics.job_title    || basics.post_name   || '',
      org:           basics.organization_name || '',
      totalVac:      basics.total_vacancies   || '',
      lastDate:      imp.last_date_to_apply   || imp.last_date || '',
      salary:        sal.pay_scale            || sal.details   || '',
      qualification: qual.education_qualification || qual.details || '',
      location:      basics.location || '',
    };

    init(row, {}, getSlug());
  }

  /* ─────────────────────────────────────────────
     6. PUBLIC API  window.TSJ_Share
  ─────────────────────────────────────────────── */
  win.TSJ_Share = {
    /**
     * Primary entry point.
     * Call from your existing renderJobPage() or injectSEO():
     *
     *   if (window.TSJ_Share) window.TSJ_Share.init(row, parsed, slug);
     */
    init: init,

    /**
     * Returns pre-built WhatsApp text for a given data object.
     * Useful if you want to display the text elsewhere.
     */
    buildWhatsAppText: function (data) {
      var slug    = data.slug || getSlug();
      var baseUrl = canonUrl(slug);
      return buildWhatsAppText(data, utm(baseUrl, 'whatsapp'));
    },

    /**
     * Re-run after dynamic slug change (e.g. SPA navigation).
     */
    refresh: function () {
      tryAutoHook();
    },

    config: CFG
  };

  /* ─────────────────────────────────────────────
     7. BOOT — run after DOM is ready
  ─────────────────────────────────────────────── */
  function boot() {
    // If job data already in global — hook immediately
    if (win.__tsjRawJob) {
      tryAutoHook();
    }

    // Also listen for the custom event job.html fires after render
    doc.addEventListener('tsj:jobRendered', function (e) {
      var d = (e && e.detail) || {};
      init(d.row, d.parsed, d.slug);
    });

    // MutationObserver fallback: detect when #jbTitle gets populated
    // (covers cases where job.html sets textContent directly)
    var titleEl = doc.getElementById('jbTitle');
    if (titleEl && !titleEl.textContent.trim()) {
      var mo = new MutationObserver(function (mutations, obs) {
        var name = titleEl.textContent.trim();
        if (!name) return;
        obs.disconnect();
        // Delay 1 frame so job.html can finish setting all fields
        requestAnimationFrame(function () {
          tryAutoHook();
        });
      });
      mo.observe(titleEl, { childList: true, characterData: true, subtree: true });
    }
  }

  if (doc.readyState === 'loading') {
    doc.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

}(window, document));
