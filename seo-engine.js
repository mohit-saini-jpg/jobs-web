/**
 * ╔══════════════════════════════════════════════════════════════╗
 * ║     TOP SARKARI JOBS — ENTERPRISE SEO ENGINE v3.0           ║
 * ║     Automatic • Dynamic • Schema-Rich • CTR-Optimized       ║
 * ╚══════════════════════════════════════════════════════════════╝
 *
 * PLACE THIS FILE: /seo-engine.js  (root of your website)
 * LOAD IN EVERY PAGE:
 *   <script src="/seo-engine.js"></script>   ← in <head>, no defer/async
 *
 * What this module does automatically:
 *   ✅ Dynamic meta title + description with high-CTR patterns
 *   ✅ Canonical URL management (www-enforced, clean URLs)
 *   ✅ BreadcrumbList schema per page
 *   ✅ FAQPage schema auto-generated from section/job context
 *   ✅ JobPosting schema (rich results eligible)
 *   ✅ WebPage / ItemList schema
 *   ✅ Open Graph + Twitter Card update
 *   ✅ robots meta (noindex for ?url= iframe pages)
 *   ✅ hreflang for en-IN
 *   ✅ Related-jobs internal linking injection
 *   ✅ Image ALT enforcement
 *   ✅ H1/H2 heading structure validation + injection
 */

(function (w, d) {
  'use strict';

  /* ══════════════════════════════════════════════════════
     0. CONSTANTS
  ══════════════════════════════════════════════════════ */
  var SITE      = 'https://www.topsarkarijobs.com';
  var SITE_NAME = 'Top Sarkari Jobs';
  var YEAR      = new Date().getFullYear();

  /* Section-to-human-label map for breadcrumbs & titles */
  var SECTION_META = {
    'latest jobs':            { label: 'Latest Sarkari Jobs',   emoji: '🔴', kw: 'latest government jobs' },
    'upcoming-jobs':          { label: 'Upcoming Sarkari Jobs', emoji: '📅', kw: 'upcoming government jobs' },
    'offline jobs':           { label: 'Offline Jobs',          emoji: '📋', kw: 'offline sarkari jobs' },
    'central jobs':           { label: 'Central Govt Jobs',     emoji: '🏛️', kw: 'central government jobs' },
    '10th pass jobs':         { label: '10th Pass Jobs',        emoji: '📗', kw: '10th pass sarkari jobs' },
    '12th pass jobs':         { label: '12th Pass Jobs',        emoji: '📘', kw: '12th pass sarkari jobs' },
    '8th pass':               { label: '8th Pass Jobs',         emoji: '📙', kw: '8th pass sarkari jobs' },
    'top 20 jobs':            { label: 'Top 20 Jobs',           emoji: '⭐', kw: 'top government jobs' },
    'graduation jobs':        { label: 'Graduation Jobs',       emoji: '🎓', kw: 'graduation pass govt jobs' },
    'haryana all state jobs': { label: 'Haryana State Jobs',    emoji: '🏅', kw: 'haryana sarkari jobs' },
    'important csc link':     { label: 'CSC Links',             emoji: '🔗', kw: 'CSC common service centre' },
    'top headlines today':    { label: "Today's Headlines",     emoji: '📰', kw: 'sarkari news today' },
    'sarkari result':         { label: 'Sarkari Results',       emoji: '📊', kw: 'latest sarkari result 2026' },
    'admit cards exams date': { label: 'Admit Cards & Exam Dates', emoji: '🎫', kw: 'admit card download 2026' },
    'railway jobs':           { label: 'Railway Jobs',          emoji: '🚂', kw: 'railway sarkari jobs 2026' },
    'bank jobs':              { label: 'Bank Jobs',             emoji: '🏦', kw: 'bank sarkari jobs 2026' },
    'police jobs':            { label: 'Police Jobs',           emoji: '👮', kw: 'police sarkari jobs 2026' },
    'ssc jobs':               { label: 'SSC Jobs',              emoji: '📝', kw: 'SSC CGL CHSL jobs 2026' },
    'upsc jobs':              { label: 'UPSC Jobs',             emoji: '🏆', kw: 'UPSC IAS IPS jobs 2026' },
    'teacher jobs':           { label: 'Teaching Jobs',         emoji: '📚', kw: 'teacher government jobs 2026' },
    'indian army jobs':       { label: 'Army Jobs',             emoji: '🪖', kw: 'Indian Army recruitment 2026' },
    'iti jobs':               { label: 'ITI Jobs',              emoji: '🔧', kw: 'ITI pass sarkari jobs' },
    'diploma jobs':           { label: 'Diploma Jobs',          emoji: '📜', kw: 'diploma sarkari jobs 2026' },
    'b.tech jobs':            { label: 'B.Tech / Engineering Jobs', emoji: '💻', kw: 'engineering sarkari jobs 2026' },
    'latest notifications':   { label: 'Latest Notifications',  emoji: '🔔', kw: 'sarkari job notifications 2026' },
  };

  /* FAQ templates keyed by section type */
  var SECTION_FAQ = {
    'latest jobs': [
      { q: 'Which are the latest sarkari jobs in ' + YEAR + '?', a: 'Latest government jobs in ' + YEAR + ' include posts from SSC, Railway, Banking, Police, Defence, UPSC and State PSC — updated daily on ' + SITE_NAME + '.' },
      { q: 'How to apply for sarkari jobs online?', a: 'Click on any job listing to see eligibility, last date and official apply link. Most central govt jobs allow online application via the official recruitment portal.' },
      { q: 'What documents are needed for government job applications?', a: 'You typically need your Aadhar, mark sheets, caste certificate (if applicable), passport-size photo, and signature in prescribed format.' },
      { q: 'Is there any age relaxation for OBC/SC/ST candidates?', a: 'Yes — OBC gets 3 years relaxation, SC/ST gets 5 years, and PwD gets 10 years over the general upper age limit as per DoPT rules.' },
    ],
    '10th pass jobs': [
      { q: 'What sarkari jobs can 10th pass candidates apply for in ' + YEAR + '?', a: 'MTS (Multi-Tasking Staff), Constable, LDC, Peon, Chowkidar, Group D Railway posts and State police constable recruitment are open for 10th pass candidates.' },
      { q: 'What is the salary for 10th pass government jobs?', a: '10th pass government jobs offer salary in Pay Level 1 (₹18,000–₹56,900) per 7th Pay Commission, plus DA, HRA and other allowances.' },
      { q: 'Does SSC recruit 10th pass candidates?', a: 'Yes, SSC MTS (Multi-Tasking Staff) is specifically for 10th pass candidates. Notification comes out annually.' },
    ],
    'railway jobs': [
      { q: 'Which railway board releases recruitment in ' + YEAR + '?', a: 'RRB (Railway Recruitment Board) and RRC (Railway Recruitment Cell) release Group D, NTPC, ALP, JE and other posts across 21 regional boards.' },
      { q: 'What is the age limit for railway jobs?', a: 'Age limit for railway recruitment is generally 18–33 years for most posts, with relaxation for SC/ST (5 yrs), OBC (3 yrs), and PwD (10 yrs).' },
      { q: 'Is there negative marking in RRB exams?', a: 'Yes, RRB CBT exams have 1/3 negative marking for every wrong answer.' },
    ],
    'upcoming-jobs': [
      { q: 'Which big sarkari job notifications are expected in ' + YEAR + '?', a: 'Expected upcoming recruitment in ' + YEAR + ' includes SSC CGL, SSC CHSL, Railway NTPC, IBPS PO/Clerk, UPSC Civil Services, NDA and State PSC exams.' },
      { q: 'How to prepare for upcoming government exams?', a: 'Start with the official syllabus, practice previous year papers, focus on GK, Maths and English sections, and track notifications on ' + SITE_NAME + ' daily.' },
    ],
    'bank jobs': [
      { q: 'Which banks recruit through IBPS in ' + YEAR + '?', a: 'IBPS conducts recruitment for 12 nationalized banks including PNB, BOB, Canara Bank, Union Bank, Bank of India and others for PO, Clerk, SO and RRB posts.' },
      { q: 'What is the salary of a bank PO?', a: 'Starting basic salary of a bank PO is approximately ₹36,000–₹42,000 per month under the 11th bipartite settlement, with additional allowances.' },
    ],
    'default': [
      { q: 'How often are sarkari job notifications updated on this site?', a: SITE_NAME + ' updates government job notifications, results, and admit cards every day to ensure you never miss an opportunity.' },
      { q: 'Can I get sarkari job alerts on mobile?', a: 'Yes, bookmark ' + SITE_NAME + ' and allow notifications. We also provide category-wise job listings so you can directly find jobs matching your qualification.' },
      { q: 'How do I check my sarkari result?', a: 'Go to the Results section on ' + SITE_NAME + ' or click directly on your exam name. We link to official result pages with download links.' },
      { q: 'Are government jobs available for all educational qualifications?', a: 'Yes — from 8th Pass to Postgraduate, there are government jobs for every qualification level. Use our category filter to find jobs matching your education.' },
    ]
  };

  /* ══════════════════════════════════════════════════════
     1. UTILITIES
  ══════════════════════════════════════════════════════ */
  function qs(sel, ctx) { return (ctx || d).querySelector(sel); }
  function qsa(sel, ctx) { return Array.prototype.slice.call((ctx || d).querySelectorAll(sel)); }

  function getParam(name) {
    return new URLSearchParams(w.location.search).get(name) || '';
  }

  function setMeta(selector, attr, value) {
    var el = qs(selector);
    if (el) el.setAttribute(attr, value);
    else {
      el = d.createElement('meta');
      // parse selector like 'meta[property="og:title"]'
      var propMatch = selector.match(/\[(\w+)="([^"]+)"\]/);
      if (propMatch) { el.setAttribute(propMatch[1], propMatch[2]); el.setAttribute(attr, value); d.head.appendChild(el); }
    }
  }

  function setOrCreate(tagName, id, attrs, content) {
    var el = d.getElementById(id) || qs(tagName + '[id="' + id + '"]');
    if (!el) { el = d.createElement(tagName); d.head.appendChild(el); }
    if (id) el.id = id;
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    if (content !== undefined) el.textContent = content;
    return el;
  }

  function slugify(str) {
    return (str || '').toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
  }

  function titleCase(str) {
    return (str || '').replace(/\w\S*/g, function(t) { return t.charAt(0).toUpperCase() + t.substr(1).toLowerCase(); });
  }

  function getSectionMeta(raw) {
    var key = (raw || '').toLowerCase().trim();
    for (var k in SECTION_META) {
      if (key.indexOf(k) !== -1 || k.indexOf(key) !== -1) return SECTION_META[k];
    }
    return null;
  }

  function getFAQ(sectionKey) {
    var k = (sectionKey || '').toLowerCase();
    for (var key in SECTION_FAQ) {
      if (key !== 'default' && k.indexOf(key) !== -1) return SECTION_FAQ[key];
    }
    return SECTION_FAQ['default'];
  }

  /* ══════════════════════════════════════════════════════
     2. CANONICAL & WWW ENFORCEMENT
  ══════════════════════════════════════════════════════ */
  function enforceCanonical(overrideUrl) {
    var canonical = d.getElementById('canonicalTag') || qs('link[rel="canonical"]');
    if (!canonical) {
      canonical = d.createElement('link');
      canonical.rel = 'canonical';
      d.head.appendChild(canonical);
    }

    var url = overrideUrl || w.location.href;
    // Enforce www
    url = url.replace('://topsarkarijobs.com', '://www.topsarkarijobs.com');
    // Remove duplicate slashes
    url = url.replace(/([^:]\/)\/+/g, '$1');

    canonical.href = url;

    // Also add hreflang
    var hreflang = d.getElementById('hreflang-in') || d.createElement('link');
    hreflang.id = 'hreflang-in';
    hreflang.rel = 'alternate';
    hreflang.hreflang = 'en-IN';
    hreflang.href = url;
    if (!d.getElementById('hreflang-in')) d.head.appendChild(hreflang);

    return url;
  }

  /* ══════════════════════════════════════════════════════
     3. TITLE & DESCRIPTION GENERATOR
     Patterns optimized for high CTR in sarkari niche
  ══════════════════════════════════════════════════════ */
  function generateTitle(context) {
    var type    = context.type    || 'home';
    var section = context.section || '';
    var jobName = context.jobName || '';
    var meta    = context.meta;   // SECTION_META entry

    var label = (meta && meta.label) || titleCase(section) || SITE_NAME;
    var emoji = (meta && meta.emoji) || '✅';

    switch (type) {
      case 'section':
        return emoji + ' ' + label + ' ' + YEAR + ' – Apply Now | ' + SITE_NAME;

      case 'job':
        // e.g. "BPSSC Havildar Recruitment 2026 – Apply Online | 344 Posts"
        var clean = jobName.replace(/\s*-\s*apply (online|offline)/i, '').replace(/\s*online form$/i, '').trim();
        return clean + ' | Apply Now ' + YEAR + ' – ' + SITE_NAME;

      case 'result':
        return '📊 Sarkari Result ' + YEAR + ' – Latest Results, Merit List | ' + SITE_NAME;

      case 'admit-card':
        return '🎫 Admit Card Download ' + YEAR + ' – All Exam Hall Tickets | ' + SITE_NAME;

      case 'category':
        return emoji + ' ' + label + ' – All Govt Jobs | ' + SITE_NAME;

      case 'home':
      default:
        return '🏆 Top Sarkari Jobs ' + YEAR + ' – Latest Govt Jobs, Results, Admit Cards | India No.1';
    }
  }

  function generateDescription(context) {
    var type    = context.type    || 'home';
    var section = context.section || '';
    var jobName = context.jobName || '';
    var meta    = context.meta;

    var label = (meta && meta.label) || titleCase(section);
    var kw    = (meta && meta.kw)    || label + ' ' + YEAR;

    switch (type) {
      case 'section':
        return '✅ ' + label + ' ' + YEAR + ': Find all latest ' + kw + ' notifications, eligibility, last date & direct apply links. Updated daily on ' + SITE_NAME + '. Don\'t miss any opportunity!';

      case 'job':
        return '📋 ' + jobName.replace(/ – .*/, '') + ': Check vacancy details, eligibility, salary, important dates & direct official apply link on ' + SITE_NAME + '. Apply before last date!';

      case 'result':
        return '📊 Check latest Sarkari Results ' + YEAR + ': SSC, Railway, Banking, Police & State Exam results with merit list, cut-off & scorecard download links – Updated daily.';

      case 'admit-card':
        return '🎫 Download Admit Card ' + YEAR + ' for SSC, Railway, IBPS, Police, UPSC & all State Exams. Hall ticket, exam date, reporting time – all in one place on ' + SITE_NAME + '.';

      case 'home':
      default:
        return '🏆 ' + SITE_NAME + ' ' + YEAR + ': India\'s No.1 source for latest Government Jobs, Sarkari Result, Admit Card, Answer Key & Online Forms. SSC, Railway, Banking, Police, UPSC – Updated Daily!';
    }
  }

  /* ══════════════════════════════════════════════════════
     4. SCHEMA GENERATORS
  ══════════════════════════════════════════════════════ */
  function injectSchema(id, obj) {
    var el = d.getElementById(id) || d.createElement('script');
    el.id   = id;
    el.type = 'application/ld+json';
    el.textContent = JSON.stringify(obj);
    if (!d.getElementById(id)) d.head.appendChild(el);
  }

  function buildBreadcrumb(items) {
    return {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      'itemListElement': items.map(function(item, i) {
        var entry = { '@type': 'ListItem', 'position': i + 1, 'name': item.name };
        if (item.url) entry.item = item.url;
        return entry;
      })
    };
  }

  function buildFAQSchema(faqs) {
    return {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      'mainEntity': faqs.map(function(f) {
        return {
          '@type': 'Question',
          'name': f.q,
          'acceptedAnswer': { '@type': 'Answer', 'text': f.a }
        };
      })
    };
  }

  function buildJobPostingSchema(job) {
    var schema = {
      '@context': 'https://schema.org',
      '@type': 'JobPosting',
      'title': job.title || 'Government Job',
      'description': job.desc || 'Apply for ' + (job.title || 'this government job') + ' on ' + SITE_NAME + '. Check eligibility, salary, last date and official apply link.',
      'hiringOrganization': {
        '@type': 'Organization',
        'name': job.org || 'Government of India',
        'sameAs': SITE
      },
      'jobLocation': {
        '@type': 'Place',
        'address': {
          '@type': 'PostalAddress',
          'addressCountry': 'IN',
          'addressLocality': job.location || 'India'
        }
      },
      'datePosted': job.datePosted || new Date().toISOString().split('T')[0],
      'employmentType': 'FULL_TIME',
      'applicantLocationRequirements': { '@type': 'Country', 'name': 'India' },
      'jobBenefits': 'Government Job Benefits: DA, HRA, TA, Medical, Pension as per 7th Pay Commission',
      'industry': 'Government / Public Sector',
      'workHours': '40 hours per week'
    };
    if (job.salary) schema.baseSalary = {
      '@type': 'MonetaryAmount',
      'currency': 'INR',
      'value': { '@type': 'QuantitativeValue', 'value': job.salary, 'unitText': 'MONTH' }
    };
    if (job.lastDate) schema.validThrough = job.lastDate;
    if (job.totalVacancies) schema.totalJobOpenings = parseInt(job.totalVacancies) || undefined;
    if (job.applyUrl) schema.url = job.applyUrl;
    return schema;
  }

  function buildItemListSchema(items, listName, pageUrl) {
    return {
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      'name': listName,
      'url': pageUrl,
      'numberOfItems': items.length,
      'itemListElement': items.slice(0, 20).map(function(item, i) {
        return {
          '@type': 'ListItem',
          'position': i + 1,
          'name': item.name || item.title || ('Job ' + (i + 1)),
          'url': item.url || (SITE + '/jobs/' + slugify(item.name || item.title || '') + '/')
        };
      })
    };
  }

  /* ══════════════════════════════════════════════════════
     5. OPEN GRAPH & TWITTER CARD UPDATE
  ══════════════════════════════════════════════════════ */
  function updateSocialMeta(title, desc, url) {
    setMeta('meta[property="og:title"]',       'content', title);
    setMeta('meta[property="og:description"]', 'content', desc);
    setMeta('meta[property="og:url"]',         'content', url);
    setMeta('meta[name="twitter:title"]',      'content', title);
    setMeta('meta[name="twitter:description"]','content', desc);
  }

  /* ══════════════════════════════════════════════════════
     6. INJECT FAQ HTML BLOCK
  ══════════════════════════════════════════════════════ */
  function injectFAQBlock(faqs, container) {
    if (!container || !faqs || !faqs.length) return;
    var existing = d.getElementById('seo-faq-block');
    if (existing) existing.remove();

    var wrap = d.createElement('section');
    wrap.id = 'seo-faq-block';
    wrap.setAttribute('itemscope', '');
    wrap.setAttribute('itemtype', 'https://schema.org/FAQPage');
    wrap.style.cssText = 'background:#f8fafc;border-radius:12px;padding:20px 24px;margin:24px 0;border:1px solid #e2e8f0;';

    var h2 = d.createElement('h2');
    h2.style.cssText = 'font-size:1.1rem;font-weight:700;color:#1e40af;margin-bottom:12px;';
    h2.textContent = 'Frequently Asked Questions (FAQ)';
    wrap.appendChild(h2);

    faqs.forEach(function(f) {
      var div = d.createElement('div');
      div.setAttribute('itemscope', '');
      div.setAttribute('itemprop', 'mainEntity');
      div.setAttribute('itemtype', 'https://schema.org/Question');
      div.style.cssText = 'border-top:1px solid #e2e8f0;padding:10px 0;';

      var q = d.createElement('h3');
      q.setAttribute('itemprop', 'name');
      q.style.cssText = 'font-size:.9rem;font-weight:600;color:#1e293b;margin:0 0 6px;cursor:pointer;';
      q.textContent = f.q;

      var ans = d.createElement('div');
      ans.setAttribute('itemscope', '');
      ans.setAttribute('itemprop', 'acceptedAnswer');
      ans.setAttribute('itemtype', 'https://schema.org/Answer');
      var p = d.createElement('p');
      p.setAttribute('itemprop', 'text');
      p.style.cssText = 'font-size:.85rem;color:#475569;margin:0;';
      p.textContent = f.a;
      ans.appendChild(p);

      div.appendChild(q);
      div.appendChild(ans);
      wrap.appendChild(div);
    });

    container.appendChild(wrap);
  }

  /* ══════════════════════════════════════════════════════
     7. INTERNAL LINKING — RELATED JOBS
  ══════════════════════════════════════════════════════ */
  var POPULAR_SECTIONS = [
    { label: '🔴 Latest Jobs',    href: '/section/latest-jobs/',     kw: ['latest', 'new', 'recent'] },
    { label: '📅 Upcoming Jobs',  href: '/section/upcoming-jobs/',   kw: ['upcoming', 'future', 'expected'] },
    { label: '🚂 Railway Jobs',   href: '/section/railway-jobs/',    kw: ['railway', 'rrb', 'rrb ntpc'] },
    { label: '🏦 Bank Jobs',      href: '/section/bank-jobs/',       kw: ['bank', 'ibps', 'sbi'] },
    { label: '👮 Police Jobs',    href: '/section/police-jobs/',     kw: ['police', 'constable', 'si'] },
    { label: '📗 10th Pass Jobs', href: '/section/10th-pass-jobs/',  kw: ['10th', '10 pass', 'mts', 'group d'] },
    { label: '📘 12th Pass Jobs', href: '/section/12th-pass-jobs/',  kw: ['12th', 'intermediate'] },
    { label: '🏆 UPSC Jobs',      href: '/section/upsc-jobs/',       kw: ['upsc', 'ias', 'ips'] },
    { label: '📝 SSC Jobs',       href: '/section/ssc-jobs/',        kw: ['ssc', 'cgl', 'chsl'] },
    { label: '📚 Teaching Jobs',  href: '/section/teaching-jobs/',   kw: ['teacher', 'teaching', 'professor', 'lecturer'] },
  ];

  function injectRelatedLinks(container, sectionKey) {
    if (!container) return;
    var existing = d.getElementById('seo-related-links');
    if (existing) return; // already injected

    var sk = (sectionKey || '').toLowerCase();
    var links = POPULAR_SECTIONS.filter(function(s) {
      // exclude current section
      return !s.kw.some(function(k) { return sk.indexOf(k) !== -1; });
    }).slice(0, 6);

    if (!links.length) return;

    var wrap = d.createElement('div');
    wrap.id = 'seo-related-links';
    wrap.style.cssText = 'margin:20px 0;padding:16px;background:#eff6ff;border-radius:10px;border:1px solid #bfdbfe;';

    var h3 = d.createElement('h3');
    h3.style.cssText = 'font-size:.9rem;font-weight:700;color:#1e40af;margin:0 0 10px;';
    h3.textContent = '🔗 More Government Job Categories';
    wrap.appendChild(h3);

    var ul = d.createElement('ul');
    ul.style.cssText = 'list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:8px;';
    links.forEach(function(lnk) {
      var li = d.createElement('li');
      var a  = d.createElement('a');
      a.href = lnk.href;
      a.textContent = lnk.label;
      a.style.cssText = 'display:inline-block;padding:6px 12px;background:#fff;border:1px solid #93c5fd;border-radius:20px;font-size:.8rem;color:#1d4ed8;font-weight:600;text-decoration:none;transition:background .2s;';
      a.addEventListener('mouseenter', function() { this.style.background = '#dbeafe'; });
      a.addEventListener('mouseleave', function() { this.style.background = '#fff'; });
      li.appendChild(a);
      ul.appendChild(li);
    });
    wrap.appendChild(ul);
    container.appendChild(wrap);
  }

  /* ══════════════════════════════════════════════════════
     8. IMAGE ALT ENFORCEMENT
  ══════════════════════════════════════════════════════ */
  function enforceImageAlts(context) {
    var fallback = (context && context.jobName) || SITE_NAME + ' ' + YEAR;
    qsa('img').forEach(function(img) {
      if (!img.getAttribute('alt') || img.getAttribute('alt').trim() === '') {
        var src  = img.src || '';
        var name = src.split('/').pop().replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ');
        img.setAttribute('alt', name || fallback);
        img.setAttribute('title', name || fallback);
      }
    });
  }

  /* ══════════════════════════════════════════════════════
     9. HEADING STRUCTURE VALIDATION
  ══════════════════════════════════════════════════════ */
  function ensureH1(text) {
    var existing = qs('h1');
    if (existing) {
      if (!existing.textContent.trim()) existing.textContent = text;
      return;
    }
    // Insert a visually-hidden H1 for SEO if none exists
    var h1 = d.createElement('h1');
    h1.textContent = text;
    h1.style.cssText = 'position:absolute;left:-9999px;font-size:1px;';
    var main = qs('main') || qs('[role="main"]') || d.body;
    if (main.firstChild) main.insertBefore(h1, main.firstChild);
    else main.appendChild(h1);
  }

  /* ══════════════════════════════════════════════════════
     10. PAGE-TYPE DETECTION & ORCHESTRATION
  ══════════════════════════════════════════════════════ */
  function detectPageType() {
    var path    = w.location.pathname.replace(/\/+$/, '').toLowerCase();
    var section = getParam('section');
    var urlP    = getParam('url');
    var slug    = (path.match(/\/jobs\/([^\/]+)/) || [])[1];

    if (path === '' || path === '/index.html' || path === '/') return { type: 'home' };
    if (slug) return { type: 'job', slug: slug };
    if (section) return { type: 'section', section: section };
    if (urlP) return { type: 'tool', url: urlP };
    if (path.indexOf('result') !== -1) return { type: 'result' };
    if (path.indexOf('admit') !== -1)  return { type: 'admit-card' };
    if (path.indexOf('category') !== -1) {
      var group = getParam('group');
      return { type: 'category', group: group };
    }
    return { type: 'page', path: path };
  }

  /* ══════════════════════════════════════════════════════
     11. MAIN INIT — runs on DOMContentLoaded
  ══════════════════════════════════════════════════════ */
  function init() {
    var pageInfo = detectPageType();
    var canonUrl = enforceCanonical();

    var title, desc, breadcrumbs, faqs;

    /* ── HOME ── */
    if (pageInfo.type === 'home') {
      title = generateTitle({ type: 'home' });
      desc  = generateDescription({ type: 'home' });
      breadcrumbs = [{ name: 'Home', url: SITE + '/' }];
      faqs  = getFAQ('latest jobs');

      injectSchema('schema-webpage', {
        '@context': 'https://schema.org',
        '@type': 'WebPage',
        'url': SITE + '/',
        'name': title,
        'description': desc,
        'inLanguage': 'en-IN',
        'dateModified': new Date().toISOString().split('T')[0],
        'isPartOf': { '@type': 'WebSite', 'url': SITE + '/', 'name': SITE_NAME }
      });
    }

    /* ── SECTION (view.html?section=) ── */
    else if (pageInfo.type === 'section') {
      var sec  = pageInfo.section;
      var meta = getSectionMeta(sec);
      var context = { type: 'section', section: sec, meta: meta };
      title = generateTitle(context);
      desc  = generateDescription(context);
      faqs  = getFAQ(sec);

      var sectionLabel = (meta && meta.label) || titleCase(sec);
      // Clean canonical: /section/latest-jobs/
      var cleanSlug = slugify(sec);
      var cleanUrl  = SITE + '/section/' + cleanSlug + '/';
      enforceCanonical(cleanUrl);

      breadcrumbs = [
        { name: 'Home',         url: SITE + '/' },
        { name: sectionLabel,   url: cleanUrl }
      ];

      // robots: tool/iframe pages should be noindex
      if (getParam('url')) {
        setMeta('meta[name="robots"]', 'content', 'noindex, nofollow');
      }

      // Wait for DOM content to be fully loaded before injecting related links
      var mainEl = qs('main') || qs('#section-view') || qs('.container') || d.body;
      setTimeout(function() {
        injectRelatedLinks(qs('#sectionSearchResults') ? qs('#section-view') : mainEl, sec);
        injectFAQBlock(faqs, mainEl);
      }, 800);

      ensureH1(sectionLabel + ' ' + YEAR + ' – ' + SITE_NAME);
    }

    /* ── JOB DETAIL ── */
    else if (pageInfo.type === 'job') {
      // job.html reads job data from JSON; we hook in after job render
      w.__SEO_ENGINE_JOB_READY = function(job) {
        var jTitle = (job && job.title) || (pageInfo.slug || '').replace(/-/g, ' ');
        var context = { type: 'job', jobName: jTitle };
        title = generateTitle(context);
        desc  = generateDescription(context);

        d.title = title;
        updateSocialMeta(title, desc, w.location.href);
        enforceCanonical(SITE + '/jobs/' + (job.slug || pageInfo.slug) + '/');

        breadcrumbs = [
          { name: 'Home', url: SITE + '/' },
          { name: 'Jobs', url: SITE + '/jobs-index.html' },
          { name: jTitle }
        ];
        injectSchema('schema-breadcrumb', buildBreadcrumb(breadcrumbs));

        // Full JobPosting schema
        injectSchema('schema-jobposting', buildJobPostingSchema({
          title: jTitle,
          desc: desc,
          org: job.organization || job.org || '',
          location: job.state || 'India',
          datePosted: job.datePosted || job.date || '',
          lastDate: job.lastDate || job.last_date || '',
          salary: job.salary || '',
          totalVacancies: job.totalVacancies || job.vacancies || '',
          applyUrl: w.location.href
        }));

        // FAQ
        var jFaqs = [
          { q: 'What is the last date to apply for ' + jTitle + '?', a: 'Check the official notification or the "Important Dates" table on this page for the exact last date. Apply well before the deadline to avoid technical issues.' },
          { q: 'How many vacancies are there in ' + jTitle + '?', a: 'See the "Vacancy Details" table above for total posts, category-wise breakdown and reservation details.' },
          { q: 'What is the eligibility for ' + jTitle + '?', a: 'Educational qualification, age limit and other eligibility criteria are mentioned in the notification. Refer to the "Eligibility" section above.' },
          { q: 'How to apply for ' + jTitle + '?', a: 'Click the "Apply Online" or "Official Notification" button above. You will be redirected to the official recruitment portal.' },
        ];
        injectSchema('schema-faq', buildFAQSchema(jFaqs));
        injectFAQBlock(jFaqs, qs('main') || d.body);
        enforceImageAlts({ jobName: jTitle });
        ensureH1(jTitle);
      };
      return; // rest of init handled by callback
    }

    /* ── RESULT PAGE ── */
    else if (pageInfo.type === 'result') {
      title = generateTitle({ type: 'result' });
      desc  = generateDescription({ type: 'result' });
      faqs  = getFAQ('sarkari result');
      breadcrumbs = [
        { name: 'Home', url: SITE + '/' },
        { name: 'Sarkari Results', url: SITE + '/result.html' }
      ];
      ensureH1('Sarkari Result ' + YEAR + ' – Latest Government Exam Results');
    }

    /* ── ADMIT CARD ── */
    else if (pageInfo.type === 'admit-card') {
      title = generateTitle({ type: 'admit-card' });
      desc  = generateDescription({ type: 'admit-card' });
      faqs  = getFAQ('admit cards exams date');
      breadcrumbs = [
        { name: 'Home', url: SITE + '/' },
        { name: 'Admit Cards', url: SITE + '/admit-card.html' }
      ];
      ensureH1('Admit Card Download ' + YEAR + ' – All Exam Hall Tickets');
    }

    /* ── TOOL / URL IFRAME ── */
    else if (pageInfo.type === 'tool') {
      // Noindex iframe/tool pages — they're not real content
      setMeta('meta[name="robots"]', 'content', 'noindex, nofollow');
      return;
    }

    /* ── CATEGORY ── */
    else if (pageInfo.type === 'category') {
      var grp = pageInfo.group || '';
      var meta2 = getSectionMeta(grp);
      title = generateTitle({ type: 'category', section: grp, meta: meta2 });
      desc  = generateDescription({ type: 'section', section: grp, meta: meta2 });
      faqs  = getFAQ(grp);
      breadcrumbs = [
        { name: 'Home', url: SITE + '/' },
        { name: titleCase(grp) || 'Category' }
      ];
    }

    /* ── GENERIC / STATIC PAGE ── */
    else {
      return; // don't override static pages
    }

    /* ── APPLY ALL ── */
    if (title) {
      d.title = title;
      updateSocialMeta(title, desc, canonUrl);
      setMeta('meta[name="description"]', 'content', desc);
    }

    if (breadcrumbs) {
      injectSchema('schema-breadcrumb', buildBreadcrumb(breadcrumbs));
    }

    if (faqs && faqs.length) {
      injectSchema('schema-faq', buildFAQSchema(faqs));
    }

    enforceImageAlts();

    // Inject FAQ HTML on next tick (after page renders)
    if (faqs && faqs.length && pageInfo.type !== 'home') {
      setTimeout(function() {
        var target = qs('main') || qs('.container') || qs('[role="main"]') || d.body;
        injectFAQBlock(faqs, target);
      }, 600);
    }
  }

  /* ══════════════════════════════════════════════════════
     12. SECTION PAGE CLEAN-URL HELPERS (for view.html)
  ══════════════════════════════════════════════════════ */
  w.__SEO_updateSection = function(sectionName, items) {
    var meta = getSectionMeta(sectionName);
    var context = { type: 'section', section: sectionName, meta: meta };
    var title = generateTitle(context);
    var desc  = generateDescription(context);
    var faqs  = getFAQ(sectionName);
    var cleanSlug = slugify(sectionName);
    var cleanUrl  = SITE + '/section/' + cleanSlug + '/';

    d.title = title;
    updateSocialMeta(title, desc, cleanUrl);
    setMeta('meta[name="description"]', 'content', desc);
    enforceCanonical(cleanUrl);

    injectSchema('schema-breadcrumb', buildBreadcrumb([
      { name: 'Home', url: SITE + '/' },
      { name: (meta && meta.label) || titleCase(sectionName), url: cleanUrl }
    ]));
    injectSchema('schema-faq', buildFAQSchema(faqs));

    if (items && items.length) {
      injectSchema('schema-itemlist', buildItemListSchema(
        items.map(function(i) { return { name: i.name || i.title, url: SITE + '/jobs/' + slugify(i.name || i.title) + '/' }; }),
        (meta && meta.label) || titleCase(sectionName),
        cleanUrl
      ));
    }

    setTimeout(function() {
      var target = qs('main') || qs('#section-view') || d.body;
      injectFAQBlock(faqs, target);
      injectRelatedLinks(target, sectionName);
      enforceImageAlts({ jobName: sectionName });
      ensureH1((meta && meta.label) || titleCase(sectionName) + ' ' + YEAR);
    }, 400);
  };

  /* Expose job-ready callback trigger */
  w.__SEO_updateJob = w.__SEO_ENGINE_JOB_READY;

  /* Run init */
  if (d.readyState === 'loading') {
    d.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* Re-enforce on URL change (SPA navigation) */
  var lastHref = w.location.href;
  setInterval(function() {
    if (w.location.href !== lastHref) {
      lastHref = w.location.href;
      setTimeout(init, 300);
    }
  }, 500);

}(window, document));
