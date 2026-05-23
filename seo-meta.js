/**
 * seo-meta.js — Top Sarkari Jobs
 * Advanced SEO Meta Tag Generator & Schema Injector
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * ✅ Auto-generate SEO title from job name
 * ✅ Auto-generate meta description
 * ✅ Auto-extract keywords from job title
 * ✅ JobPosting schema (Google Jobs)
 * ✅ BreadcrumbList schema
 * ✅ FAQPage schema
 * ✅ Organization schema
 * ✅ Open Graph + Twitter Card tags
 * ✅ Canonical URL management
 * ✅ Pagination SEO (prev/next)
 * ✅ Duplicate content prevention
 * ✅ E-E-A-T signals
 */

(function () {
  'use strict';

  var SITE = 'https://www.topsarkarijobs.com';
  var SITE_NAME = 'Top Sarkari Jobs';
  var DEFAULT_IMAGE = SITE + '/image.png';

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     1. KEYWORD EXTRACTOR
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  var BASE_KEYWORDS = [
    'sarkari jobs 2026', 'government jobs 2026', 'sarkari naukri',
    'sarkari result', 'admit card 2026', 'online form 2026'
  ];

  var KEYWORD_PATTERNS = [
    { regex: /railway|rrb|rrb\s*ntpc/i, kw: ['railway jobs 2026', 'RRB recruitment', 'railway government jobs'] },
    { regex: /police|constable|sub.inspector|asi\b|si\b/i, kw: ['police jobs 2026', 'constable recruitment', 'government police vacancy'] },
    { regex: /ssc|staff.selection/i, kw: ['SSC jobs 2026', 'SSC CGL 2026', 'SSC CHSL 2026'] },
    { regex: /bank|ibps|sbi|rbi|nabard/i, kw: ['bank jobs 2026', 'IBPS recruitment', 'bank PO clerk jobs'] },
    { regex: /upsc|ias|ips|civil.service/i, kw: ['UPSC 2026', 'IAS recruitment', 'civil services exam'] },
    { regex: /army|defence|defence|military|soldier|bsf|crpf|cisf|itbp|ssb/i, kw: ['defence jobs 2026', 'army recruitment 2026', 'central armed police'] },
    { regex: /teacher|teaching|lecturer|professor|tgt|pgt|school/i, kw: ['teaching jobs 2026', 'teacher recruitment 2026', 'school government jobs'] },
    { regex: /haryana/i, kw: ['Haryana govt jobs 2026', 'Haryana sarkari naukri', 'HSSC recruitment'] },
    { regex: /up\b|uttar.pradesh/i, kw: ['UP sarkari jobs 2026', 'UPPSC recruitment', 'Uttar Pradesh govt jobs'] },
    { regex: /bihar/i, kw: ['Bihar sarkari jobs 2026', 'BPSC recruitment', 'Bihar police jobs'] },
    { regex: /rajasthan/i, kw: ['Rajasthan govt jobs 2026', 'RPSC recruitment'] },
    { regex: /10th.pass|matriculation|sslc/i, kw: ['10th pass jobs 2026', 'matric pass government job'] },
    { regex: /12th.pass|intermediate|10\+2/i, kw: ['12th pass jobs 2026', 'inter pass sarkari naukri'] },
    { regex: /iti\b/i, kw: ['ITI jobs 2026', 'ITI pass government jobs', 'ITI trade apprentice'] },
    { regex: /engineer|b\.?tech|b\.?e\b/i, kw: ['engineering jobs 2026', 'B.Tech government jobs'] },
    { regex: /nurse|nursing|health|anm|gnm|doctor/i, kw: ['health department jobs 2026', 'nursing government jobs'] },
    { regex: /result/i, kw: ['sarkari result 2026', 'government exam result'] },
    { regex: /admit.card/i, kw: ['admit card 2026', 'hall ticket download'] },
    { regex: /answer.key/i, kw: ['answer key 2026', 'official answer key download'] },
  ];

  window.TSJ_SEO = window.TSJ_SEO || {};

  window.TSJ_SEO.extractKeywords = function (title, category) {
    var keywords = BASE_KEYWORDS.slice();
    var text = (title || '') + ' ' + (category || '');

    KEYWORD_PATTERNS.forEach(function (p) {
      if (p.regex.test(text)) {
        keywords = keywords.concat(p.kw);
      }
    });

    // Extract year
    var yearMatch = text.match(/20\d\d/);
    if (yearMatch) {
      keywords.push('online form ' + yearMatch[0]);
      keywords.push('recruitment ' + yearMatch[0]);
    }

    // Add title-derived keywords
    var cleanTitle = title.replace(/[^a-zA-Z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
    if (cleanTitle.length > 10) {
      keywords.push(cleanTitle.substring(0, 60).toLowerCase());
    }

    return keywords.slice(0, 15).join(', ');
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     2. SEO TITLE GENERATOR
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.TSJ_SEO.generateTitle = function (jobTitle, suffix) {
    if (!jobTitle) return SITE_NAME + ' | Latest Sarkari Jobs 2026';
    suffix = suffix || ' | Top Sarkari Jobs';
    var base = jobTitle.trim();
    // Ensure 2026 in title for freshness signal
    if (!/20\d\d/.test(base)) base += ' 2026';
    // CTR-optimized suffix
    var suffixVariants = [
      ' – Apply Online | Top Sarkari Jobs',
      ' | Official Notification | Top Sarkari Jobs',
      ' – Eligibility, Last Date | Top Sarkari Jobs',
      ' | Salary, Vacancy Details | Top Sarkari Jobs'
    ];
    // Rotate suffix based on title hash for variety
    var hash = base.split('').reduce(function (a, c) { return a + c.charCodeAt(0); }, 0);
    suffix = suffixVariants[hash % suffixVariants.length];
    // Keep under 60 chars
    var full = base + suffix;
    if (full.length > 65) {
      base = base.substring(0, 65 - suffix.length);
      full = base + suffix;
    }
    return full;
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     3. META DESCRIPTION GENERATOR
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.TSJ_SEO.generateDescription = function (job) {
    var bd = job.basic_details || {};
    var dates = job.important_dates || {};
    var title = bd.job_title || '';
    var lastDate = dates.last_date_to_apply || dates.last_date || dates.last_date_apply || '';
    var shortInfo = bd.short_information || '';

    if (shortInfo.length > 80) {
      shortInfo = shortInfo.substring(0, 120);
    }

    var parts = [];
    if (title) parts.push(title);
    if (lastDate) parts.push('Last Date: ' + lastDate + '.');
    if (shortInfo) parts.push(shortInfo);
    parts.push('Apply Now | Top Sarkari Jobs');

    var desc = parts.join(' ').replace(/\s+/g, ' ').trim();
    if (desc.length > 160) desc = desc.substring(0, 157) + '...';
    return desc;
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     4. JOB POSTING SCHEMA (Google Jobs)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.TSJ_SEO.generateJobSchema = function (job, slug) {
    var bd = job.basic_details || {};
    var dates = job.important_dates || {};
    var fee = job.application_fee || {};
    var salary = job.salary_details || {};
    var qual = job.qualification || {};

    var title = bd.job_title || 'Government Job';
    var canonical = SITE + '/jobs/' + (slug || '') + '/';
    var lastDate = dates.last_date_to_apply || dates.last_date || dates.last_date_apply || '';

    // Parse last date to ISO format
    var validThrough = '';
    if (lastDate) {
      try {
        var parts = lastDate.match(/(\d{1,2})[-\/\s](\d{1,2}|\w+)[-\/\s](\d{2,4})/);
        if (parts) {
          var d = new Date(lastDate);
          if (!isNaN(d)) validThrough = d.toISOString().split('T')[0];
        }
      } catch (e) {}
    }
    if (!validThrough) {
      var future = new Date();
      future.setMonth(future.getMonth() + 2);
      validThrough = future.toISOString().split('T')[0];
    }

    // Salary
    var salaryText = salary.pay_scale || salary.salary || salary.pay_matrix || '';
    var salarySchema = null;
    var salaryMatch = salaryText.match(/[\d,]+/);
    if (salaryMatch) {
      var salNum = parseInt(salaryMatch[0].replace(/,/g, ''));
      if (salNum > 1000) {
        salarySchema = {
          '@type': 'MonetaryAmount',
          'currency': 'INR',
          'value': {
            '@type': 'QuantitativeValue',
            'value': salNum,
            'unitText': 'MONTH'
          }
        };
      }
    }

    var schema = {
      '@context': 'https://schema.org',
      '@type': 'JobPosting',
      '@id': canonical + '#job',
      'title': title,
      'description': (bd.short_information || title + ' – Government job recruitment in India. ' + (qual.details || '')).substring(0, 500),
      'identifier': {
        '@type': 'PropertyValue',
        'name': SITE_NAME,
        'value': slug || title
      },
      'datePosted': bd.last_updated || new Date().toISOString().split('T')[0],
      'validThrough': validThrough,
      'employmentType': ['FULL_TIME', 'OTHER'],
      'hiringOrganization': {
        '@type': 'Organization',
        'name': bd.post_name || 'Government of India',
        'sameAs': bd.official_website || SITE,
        'logo': DEFAULT_IMAGE
      },
      'jobLocation': {
        '@type': 'Place',
        'address': {
          '@type': 'PostalAddress',
          'addressCountry': 'IN',
          'addressLocality': 'India'
        }
      },
      'applicantLocationRequirements': {
        '@type': 'Country',
        'name': 'India'
      },
      'jobBenefits': 'Government Job Benefits, Job Security, Pension, Medical Benefits',
      'url': canonical,
      'directApply': false
    };

    if (salarySchema) schema.baseSalary = salarySchema;

    return schema;
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     5. BREADCRUMB SCHEMA
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.TSJ_SEO.generateBreadcrumbSchema = function (crumbs) {
    return {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      'itemListElement': crumbs.map(function (c, i) {
        return {
          '@type': 'ListItem',
          'position': i + 1,
          'name': c.name,
          'item': c.url
        };
      })
    };
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     6. FAQ SCHEMA GENERATOR
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.TSJ_SEO.generateFAQSchema = function (faqs) {
    if (!faqs || !faqs.length) return null;
    return {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      'mainEntity': faqs.slice(0, 10).map(function (f) {
        return {
          '@type': 'Question',
          'name': (f.question || '').replace(/^Q\d+\.\s*/i, '').trim(),
          'acceptedAnswer': {
            '@type': 'Answer',
            'text': (f.answer || '').substring(0, 500)
          }
        };
      })
    };
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     7. META TAG INJECTOR
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.TSJ_SEO.injectMeta = function (opts) {
    opts = opts || {};

    function setMeta(sel, attr, val) {
      if (!val) return;
      var el = document.querySelector(sel);
      if (el) {
        el.setAttribute(attr, val);
      } else {
        el = document.createElement('meta');
        var parts = sel.match(/\[(\w+)=['"]([^'"]+)['"]\]/);
        if (parts) {
          el.setAttribute(parts[1], parts[2]);
          el.setAttribute(attr, val);
          document.head.appendChild(el);
        }
      }
    }

    function setLink(rel, href) {
      if (!href) return;
      var el = document.querySelector('link[rel="' + rel + '"]');
      if (!el) {
        el = document.createElement('link');
        el.rel = rel;
        document.head.appendChild(el);
      }
      el.href = href;
    }

    function injectSchema(id, data) {
      if (!data) return;
      var el = document.getElementById(id);
      if (!el) {
        el = document.createElement('script');
        el.type = 'application/ld+json';
        el.id = id;
        document.head.appendChild(el);
      }
      el.textContent = JSON.stringify(data, null, 0);
    }

    // Title
    if (opts.title) document.title = opts.title;

    // Meta tags
    setMeta('meta[name="description"]', 'content', opts.description);
    setMeta('meta[name="keywords"]', 'content', opts.keywords);
    setMeta('meta[name="robots"]', 'content', opts.robots || 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1');
    setMeta('meta[name="author"]', 'content', opts.author || SITE_NAME);

    // Canonical
    setLink('canonical', opts.canonical);

    // Open Graph
    setMeta('meta[property="og:title"]', 'content', opts.title);
    setMeta('meta[property="og:description"]', 'content', opts.description);
    setMeta('meta[property="og:url"]', 'content', opts.canonical);
    setMeta('meta[property="og:image"]', 'content', opts.image || DEFAULT_IMAGE);
    setMeta('meta[property="og:type"]', 'content', opts.ogType || 'article');
    setMeta('meta[property="og:site_name"]', 'content', SITE_NAME);
    setMeta('meta[property="og:locale"]', 'content', 'en_IN');

    // Twitter
    setMeta('meta[name="twitter:card"]', 'content', 'summary_large_image');
    setMeta('meta[name="twitter:title"]', 'content', opts.title);
    setMeta('meta[name="twitter:description"]', 'content', opts.description);
    setMeta('meta[name="twitter:image"]', 'content', opts.image || DEFAULT_IMAGE);
    setMeta('meta[name="twitter:site"]', 'content', '@topsarkarijobs');

    // Article meta for job pages
    if (opts.datePublished) {
      setMeta('meta[property="article:published_time"]', 'content', opts.datePublished);
      setMeta('meta[property="article:modified_time"]', 'content', opts.dateModified || opts.datePublished);
      setMeta('meta[property="article:author"]', 'content', SITE_NAME);
      setMeta('meta[property="article:section"]', 'content', opts.category || 'Government Jobs');
    }

    // Pagination
    if (opts.prevUrl) setLink('prev', opts.prevUrl);
    if (opts.nextUrl) setLink('next', opts.nextUrl);

    // Schemas
    injectSchema('seo-job-schema', opts.jobSchema);
    injectSchema('seo-breadcrumb-schema', opts.breadcrumbSchema);
    injectSchema('seo-faq-schema', opts.faqSchema);
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     8. FULL JOB PAGE SEO SETUP
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.TSJ_SEO.setupJobPage = function (job, slug, category) {
    var bd = job.basic_details || {};
    var title = window.TSJ_SEO.generateTitle(bd.job_title);
    var description = window.TSJ_SEO.generateDescription(job);
    var keywords = window.TSJ_SEO.extractKeywords(bd.job_title, category);
    var canonical = SITE + '/jobs/' + slug + '/';

    var crumbs = [
      { name: 'Home', url: SITE + '/' },
      { name: 'Jobs', url: SITE + '/jobs/' },
    ];
    if (category) crumbs.push({ name: category, url: SITE + '/category/' + category.toLowerCase().replace(/\s+/g, '-') + '/' });
    crumbs.push({ name: bd.job_title || 'Job Details', url: canonical });

    window.TSJ_SEO.injectMeta({
      title: title,
      description: description,
      keywords: keywords,
      canonical: canonical,
      ogType: 'article',
      datePublished: bd.last_updated || new Date().toISOString().split('T')[0],
      dateModified: bd.last_updated || new Date().toISOString().split('T')[0],
      category: category || 'Government Jobs',
      jobSchema: window.TSJ_SEO.generateJobSchema(job, slug),
      breadcrumbSchema: window.TSJ_SEO.generateBreadcrumbSchema(crumbs),
      faqSchema: window.TSJ_SEO.generateFAQSchema(job.faq)
    });
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     9. CATEGORY PAGE SEO
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.TSJ_SEO.setupCategoryPage = function (category, jobCount) {
    var catSlug = category.toLowerCase().replace(/\s+/g, '-');
    var canonical = SITE + '/category/' + catSlug + '/';
    var title = 'Latest ' + category + ' 2026 | ' + (jobCount || '') + ' Vacancies | Top Sarkari Jobs';
    var description = 'Browse ' + (jobCount || 'latest') + ' ' + category + ' 2026. Apply online for government jobs — eligibility, salary, last date, notification. Updated daily on Top Sarkari Jobs.';

    window.TSJ_SEO.injectMeta({
      title: title,
      description: description,
      keywords: window.TSJ_SEO.extractKeywords(category, category),
      canonical: canonical,
      ogType: 'website',
      breadcrumbSchema: window.TSJ_SEO.generateBreadcrumbSchema([
        { name: 'Home', url: SITE + '/' },
        { name: category, url: canonical }
      ])
    });
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     10. INDEXNOW PING (on new jobs)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.TSJ_SEO.pingIndexNow = function (urls) {
    if (!urls || !urls.length) return;
    // IndexNow key — set your actual key here
    var key = 'topsarkarijobs-indexnow-key-2026';
    var payload = {
      host: 'www.topsarkarijobs.com',
      key: key,
      keyLocation: SITE + '/' + key + '.txt',
      urlList: urls.slice(0, 10000)
    };
    // Bing IndexNow
    fetch('https://api.indexnow.org/indexnow', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(payload)
    }).then(function (r) {
      if (r.ok) console.log('[IndexNow] Pinged', urls.length, 'URLs');
    }).catch(function (e) { console.warn('[IndexNow] Error:', e); });
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     11. RELATED JOBS GENERATOR
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.TSJ_SEO.findRelatedJobs = function (currentJob, allJobs, maxResults) {
    maxResults = maxResults || 6;
    var currentTitle = (currentJob.basic_details || {}).job_title || '';
    var currentWords = currentTitle.toLowerCase().split(/\W+/).filter(function (w) { return w.length > 3; });

    function score(job) {
      var title = ((job.basic_details || {}).job_title || '').toLowerCase();
      var s = 0;
      currentWords.forEach(function (w) { if (title.includes(w)) s++; });
      return s;
    }

    return allJobs
      .filter(function (j) {
        return j !== currentJob && ((j.basic_details || {}).job_title || '') !== currentTitle;
      })
      .map(function (j) { return { job: j, score: score(j) }; })
      .filter(function (x) { return x.score > 0; })
      .sort(function (a, b) { return b.score - a.score; })
      .slice(0, maxResults)
      .map(function (x) { return x.job; });
  };

  console.log('[TSJ SEO] Meta engine loaded ✓');

})();
