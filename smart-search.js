/**
 * ============================================================
 * TOP SARKARI JOBS – ADVANCED SMART SEARCH SYSTEM v2.0
 * Features: Fuzzy search, Fuse.js, Live dropdown, Filters,
 *           Trending tags, Recent searches, Keyboard nav,
 *           Highlight, SEO URLs, Debounce, Lazy JSON loading
 * ============================================================
 */
(function () {
  'use strict';

  /* ── CONFIG ────────────────────────────────────────────── */
  const CFG = {
    fuseJs: 'https://cdnjs.cloudflare.com/ajax/libs/fuse.js/7.0.0/fuse.min.js',
    // ✅ FIXED: Actual JSON files used by this site
    jsonFiles: [
      'merged_sarkari_data.json',
      'dailyupdates.json',
      'Complete_Jobs_Full_Data.json',
      'state-jobs-data.json',
    ],
    maxSuggest: 10,
    maxResults: 30,
    debounceMs: 200,
    recentKey: 'tsj_recent_searches',
    maxRecent: 8,
    searchPageUrl: 'search.html',
  };

  /* ── TRENDING TAGS ─────────────────────────────────────── */
  const TRENDING = [
    { label: 'Railway Jobs',   q: 'railway',   icon: 'fa-train' },
    { label: 'Police Jobs',    q: 'police',    icon: 'fa-shield-halved' },
    { label: 'Haryana Jobs',   q: 'haryana',   icon: 'fa-location-dot' },
    { label: '10th Pass Jobs', q: '10th',      icon: 'fa-certificate' },
    { label: 'Admit Card',     q: 'admit card',icon: 'fa-id-card' },
    { label: 'SSC CGL',        q: 'ssc cgl',   icon: 'fa-medal' },
    { label: 'Bank Jobs',      q: 'bank',      icon: 'fa-building-columns' },
    { label: 'Army Jobs',      q: 'army',      icon: 'fa-star' },
    { label: 'Results',        q: 'result',    icon: 'fa-trophy' },
    { label: 'ITI Jobs',       q: 'iti',       icon: 'fa-tools' },
  ];

  /* ── BUILT-IN SEED DATA (fallback when JSON not loaded) ── */
  // ── HELPER: Section slug se readable section name nikaalein ──
  function getSectionName(slug) {
    if (!slug) return 'Other';
    try {
      const url = new URL(slug, 'https://x.com');
      const section = url.searchParams.get('section');
      if (section) return decodeURIComponent(section);
    } catch(e) {}
    // fallback: slug se filename
    const base = slug.split('?')[0].split('/').pop().replace(/\.html?$/i, '');
    return base || 'Other';
  }

  /* ── REAL SEED DATA — actual jobs from merged_sarkari_data.json ──
   * Yeh data JSON load se pehle bhi search kaam karta hai (instant results).
   * Daily update karo is array ko jab JSON data update ho.
   * ──────────────────────────────────────────────────────────────── */
  const SEED_DATA = [
    { title: 'Railway RRB ALP CEN 01/2026 Online Form 2026 for 11127 Post', dept: 'Indian Railway', qual: '10th / ITI', state: 'All India', cat: 'Latest Job', tags: 'Railway RRB ALP CEN 01/2026 Online Form 2026 for 11127 Post Indian Railway Railway Recruitment Board RRB Assistant Loco Pilot ALP CEN 01/2026 railway rrb alp cen 11127 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-railway-rrb-alp-cen-012026-online-form-2026-for-11127-post-97dd53&section=Latest%20Jobs', lastDate: '2026-06-14', icon: 'fa-train', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Army 10+2 TES 56 Online Form 2026 for 90 Post January 2027 Batch', dept: 'Indian Army', qual: '10+2 with PCM', state: 'All India', cat: 'Latest Job', tags: 'Army 10+2 TES 56 Online Form 2026 for 90 Post January 2027 Batch Army Recruitment Join Indian Army TES 56 Course army tes 56 10+2 jee mains 2026 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-army-102-tes-56-online-form-2026-for-90-post-january-2027-batch-327b9e&section=Latest%20Jobs', lastDate: '2026-06-12', icon: 'fa-star', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'SBI Trade Finance Officer TFO Online Form 2026 for 100 Post', dept: 'State Bank of India', qual: 'Graduation', state: 'All India', cat: 'Latest Job', tags: 'SBI Trade Finance Officer TFO Online Form 2026 for 100 Post State Bank of India SBI Trade Finance Officer bank sbi tfo 100 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-sbi-trade-finance-officer-tfo-online-form-2026-for-100-post-0c1deb&section=Latest%20Jobs', lastDate: '2026-06-02', icon: 'fa-building-columns', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'NFL Management Trainee MT Online Form 2026 for 21 Post', dept: 'National Fertilizer Limited', qual: 'B.Tech / MBA', state: 'All India', cat: 'Latest Job', tags: 'NFL Management Trainee MT Online Form 2026 for 21 Post National Fertilizer Limited NFL Management Trainee MT 2026 nfl mt psu fertilizer management trainee sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-nfl-management-trainee-mt-online-form-2026-for-21-post-121da1&section=Latest%20Jobs', lastDate: '2026-06-12', icon: 'fa-briefcase', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'UPSSSC Various Post Online Form 2026 Through PET 2025', dept: 'UPSSSC', qual: 'PET 2025 Score Card', state: 'Uttar Pradesh', cat: 'Latest Job', tags: 'UPSSSC Various Post Online Form 2026 Through PET 2025 Uttar Pradesh Subordinate Service Selection Commission UPSSSC up various advertisements upsssc pet 2025 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-upsssc-various-post-online-form-2026-through-pet-2025-57531b&section=Latest%20Jobs', lastDate: '', icon: 'fa-medal', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Indian Air Force AFCAT 02/2026 Batch Online Form 2026', dept: 'Indian Air Force', qual: '12th / Graduation', state: 'All India', cat: 'Latest Job', tags: 'Indian Air Force AFCAT 02/2026 Batch Online Form 2026 Join Indian Air Force AFCAT July 2027 Recruitment afcat air force defence 2026 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-indian-air-force-afcat-022026-batch-online-form-2026-ad7cd7&section=Latest%20Jobs', lastDate: '2026-06-19', icon: 'fa-star', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Coal India CIL Management Trainee MT Online Form 2026 for 660 Post', dept: 'Coal India Limited', qual: 'B.Tech / MBA', state: 'All India', cat: 'Latest Job', tags: 'Coal India CIL Management Trainee MT Online Form 2026 for 660 Post Coal India Limited CIL Management Trainee cil coal india psu mt 660 management trainee sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-coal-india-cil-management-trainee-mt-online-form-2026-for-660-post-75eb44&section=Latest%20Jobs', lastDate: '2026-06-11', icon: 'fa-briefcase', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'CTET September 2026 Online Form', dept: 'CBSE', qual: 'B.Ed / D.El.Ed', state: 'All India', cat: 'Latest Job', tags: 'CTET September 2026 Online Form Central Board of Secondary Education CBSE Central Teacher Eligibility Test CTET ctet teacher eligibility test 2026 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-ctet-september-2026-online-form-bd964d&section=Latest%20Jobs', lastDate: '2026-06-10', icon: 'fa-chalkboard-user', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'CRPF Constable Tradesman Online Form 2026 for 9175 Post', dept: 'CRPF', qual: '10th Pass', state: 'All India', cat: 'Latest Job', tags: 'CRPF Constable Tradesman Online Form 2026 for 9175 Post Central Reserve Police Force CRPF Constable Tradesman Technical Pioneer crpf constable police 10th 9175 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-crpf-constable-tradesman-online-form-2026-for-9175-post-182259&section=Latest%20Jobs', lastDate: '2026-05-19', icon: 'fa-shield-halved', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Railway RRC SECR Raipur Apprentices Online Form 2026 for 1644 Post', dept: 'Indian Railway SECR', qual: '10th / ITI', state: 'All India', cat: 'Latest Job', tags: 'Railway RRC SECR Raipur Apprentices Online Form 2026 for 1644 Post Indian Railway South East Central Railway SECR Raipur Apprentices railway secr raipur apprentice iti 1644 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-railway-rrc-secr-raipur-apprentices-online-form-2026-for-1644-post-2f0dc5&section=Latest%20Jobs', lastDate: '2026-06-04', icon: 'fa-train', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Bihar BPSC 72 Pre Exam Online Form 2026 for 1186 Post', dept: 'Bihar Public Service Commission', qual: 'Graduation', state: 'Bihar', cat: 'Latest Job', tags: 'Bihar BPSC 72 Pre Exam Online Form 2026 for 1186 Post Bihar Public Service Commission BPSC 72th Integrated bpsc bihar psc state civil services graduation 1186 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-bihar-bpsc-72-pre-exam-online-form-2026-for-1186-post-c0ad34&section=Latest%20Jobs', lastDate: '2026-05-31', icon: 'fa-graduation-cap', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Rajasthan RSSB Teaching Associate Online Form 2026 for 3540 Post', dept: 'Rajasthan Staff Selection Board', qual: 'Graduation / B.Ed', state: 'Rajasthan', cat: 'Latest Job', tags: 'Rajasthan RSSB Teaching Associate Online Form 2026 for 3540 Post Rajasthan Staff Selection Board RSSB RSMSSB Contractual Teaching Associate rajasthan rssb teaching teacher 3540 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-rajasthan-rssb-teaching-associate-online-form-2026-for-3540-post-438fa4&section=Latest%20Jobs', lastDate: '2026-06-03', icon: 'fa-chalkboard-user', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'SSC Stenographer Online Form 2026 for 731 Post', dept: 'Staff Selection Commission', qual: '12th Pass', state: 'All India', cat: 'Latest Job', tags: 'SSC Stenographer Online Form 2026 for 731 Post Staff Selection Commission SSC Stenographer Grade C D ssc stenographer 12th 731 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-ssc-stenographer-online-form-2026-for-731-post-22e0b3&section=Latest%20Jobs', lastDate: '2026-05-15', icon: 'fa-medal', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'NTA UGC NET June 2026 Online Form for JRF and Assistant Professor', dept: 'NTA / UGC', qual: 'Post Graduation', state: 'All India', cat: 'Latest Job', tags: 'NTA UGC NET June 2026 Online Form for JRF and Assistant Professor National Testing Agency NTA UGC National Eligibility Test ugc net jrf assistant professor post graduation 2026 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-nta-ugc-net-june-2026-online-form-for-jrf-and-assistant-professor-0e1674&section=Latest%20Jobs', lastDate: '2026-05-20', icon: 'fa-graduation-cap', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Union Bank of India UBI Apprentices Online Form 2026 for 1865 Post', dept: 'Union Bank of India', qual: 'Graduation', state: 'All India', cat: 'Latest Job', tags: 'Union Bank of India UBI Apprentices Online Form 2026 for 1865 Post Union Bank of India UBI Apprentices Recruitment union bank apprentice banking graduation 1865 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-union-bank-of-india-ubi-apprentices-online-form-2026-for-1865-post-71b493&section=Latest%20Jobs', lastDate: '2026-05-19', icon: 'fa-building-columns', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Reserve Bank RBI Officer Grade B Online Form 2026 for 60 Post', dept: 'Reserve Bank of India', qual: 'Graduation', state: 'All India', cat: 'Latest Job', tags: 'Reserve Bank RBI Officer Grade B Online Form 2026 for 60 Post Reserve Bank of India RBI Officer Grade B rbi officer grade b banking 60 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-reserve-bank-rbi-officer-grade-b-online-form-2026-for-60-post-06e40c&section=Latest%20Jobs', lastDate: '2026-05-20', icon: 'fa-building-columns', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Navy SSC Executive IT Online Form 2026 for 15 Post', dept: 'Indian Navy', qual: 'B.Tech', state: 'All India', cat: 'Latest Job', tags: 'Navy SSC Executive IT Online Form 2026 for 15 Post Join Indian Navy Nausena Bharti SSC Executive Information Technology navy it executive defence btech 15 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-navy-ssc-executive-it-online-form-2026-for-15-post-031634&section=Latest%20Jobs', lastDate: '2026-06-01', icon: 'fa-star', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'UP Cooperative Bank Various Post Online Form 2026 for 2085 Posts', dept: 'UP Co-Operative Institutional Service Board', qual: 'Graduation', state: 'Uttar Pradesh', cat: 'Latest Job', tags: 'UP Cooperative Bank Various Post Online Form 2026 for 2085 Posts U.P. Co-Operative Institutional Service Board UPCISB Combined Co-operative Banking up cooperative bank 2085 graduation sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-up-cooperative-bank-various-post-online-form-2026-for-2085-posts-4732e4&section=Latest%20Jobs', lastDate: '2026-05-15', icon: 'fa-building-columns', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'BPSSC Havildar Instructor Online Form 2026 for 122 Post', dept: 'Bihar Police BPSSC', qual: '10+2', state: 'Bihar', cat: 'Latest Job', tags: 'BPSSC Havildar Instructor Online Form 2026 for 122 Post Bihar Police Subordinate Services Commission BPSSC Havildar Instructor bpssc havildar police 12th 122 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-bpssc-havildar-instructor-online-form-2026-for-122-post-16100a&section=Latest%20Jobs', lastDate: '2026-06-01', icon: 'fa-shield-halved', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'MPPSC Scientific Officer Biology Online Form 2026 for 25 Post', dept: 'Madhya Pradesh PSC', qual: 'M.Sc Biology', state: 'Madhya Pradesh', cat: 'Latest Job', tags: 'MPPSC Scientific Officer Biology Online Form 2026 for 25 Post Madhya Pradesh Public Service Commission MPPSC Scientific Officer Biology mppsc scientific officer mp psc 25 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-mppsc-scientific-officer-biology-online-form-2026-for-25-post-c0204c&section=Latest%20Jobs', lastDate: '2026-05-20', icon: 'fa-graduation-cap', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'UPSSSC Assistant Statistical Officer Online Form 2026 for 1565 Post', dept: 'UPSSSC', qual: 'Master Degree in Mathematics / Statistics', state: 'Uttar Pradesh', cat: 'Latest Job', tags: 'UPSSSC Assistant Statistical Officer Online Form 2026 for 1565 Post Uttar Pradesh Subordinate Service Selection Commission UPSSSC Assistant Statistical Officer ASO PET 2025 1565 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-upsssc-assistant-statistical-officer-online-form-2026-for-1565-post-f231f5&section=Latest%20Jobs', lastDate: '2026-05-15', icon: 'fa-medal', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'MPESB Hospital Assistant Online Form 2026 for 1200 Post', dept: 'MP Employee Selection Board', qual: '12th Pass', state: 'Madhya Pradesh', cat: 'Latest Job', tags: 'MPESB Hospital Assistant Online Form 2026 for 1200 Post Madhya Pradesh Employee Selection Board MPESB Hospital Assistant 2026 mpesb hospital 12th 1200 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-mpesb-hospital-assistant-online-form-2026-for-1200-post-60aa16&section=Latest%20Jobs', lastDate: '2026-05-21', icon: 'fa-stethoscope', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'Uttar Pradesh UP Anganwadi Worker Bharti Online Form 2026', dept: 'UP District Program Officer', qual: '10+2', state: 'Uttar Pradesh', cat: 'Latest Job', tags: 'Uttar Pradesh UP Anganwadi Worker Bharti Online Form 2026 UP Anganwadi Worker Bharti anganwadi worker women 10th 12th up sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-uttar-pradesh-up-anganwadi-worker-bharti-online-form-2026-c945b2&section=Latest%20Jobs', lastDate: '', icon: 'fa-heart', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'CBSE Board 12th Result 2026', dept: 'CBSE', qual: '12th Pass', state: 'All India', cat: 'Result', tags: 'CBSE Board 12th Result 2026 Central Board of Secondary Education CBSE Class 12th Result cbse 12th result board class 12 intermediate sarkari naukri 2026', slug: 'job.html?slug=sr_result-cbse-board-12th-result-2026-8cb151&section=Latest%20Jobs', lastDate: '', icon: 'fa-trophy', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Results' },
    { title: 'Railway RRB Junior Engineer JE CEN 05/2025 Result 2026', dept: 'Indian Railway', qual: 'Diploma / B.Tech', state: 'All India', cat: 'Result', tags: 'Railway RRB Junior Engineer JE CEN 05/2025 Result 2026 Railway Recruitment Board RRB Junior Engineer JE result railway rrb je result 2026 sarkari naukri 2026', slug: 'job.html?slug=sr_result-railway-rrb-junior-engineer-je-cen-052025-result-2026-02a8b9&section=Latest%20Jobs', lastDate: '', icon: 'fa-train', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Results' },
    { title: 'UPSC Civil Services IAS IFS Pre Admit Card 2026', dept: 'UPSC', qual: 'Graduation', state: 'All India', cat: 'Admit Card', tags: 'UPSC Civil Services IAS IFS Pre Admit Card 2026 Union Public Service Commission UPSC Civil Services IAS IFS upsc ias admit card pre exam 2026 sarkari naukri 2026', slug: 'job.html?slug=sr_admit_card-upsc-civil-services-ias-ifs-pre-admit-card-2026-b2c77a&section=Latest%20Jobs', lastDate: '', icon: 'fa-id-card', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Admit Cards' },
    { title: 'Railway RRB NTPC 10+2 UG Level CEN 07/2025 Exam City Details 2026', dept: 'Indian Railway', qual: '12th Pass', state: 'All India', cat: 'Admit Card', tags: 'Railway RRB NTPC 10+2 UG Level CEN 07/2025 Exam City Details 2026 Railway Recruitment Board NTPC UnderGraduate Level railway rrb ntpc ug 12th admit card 2026 sarkari naukri 2026', slug: 'job.html?slug=sr_admit_card-railway-rrb-ntpc-102-ug-level-cen-072025-exam-city-details-2026-9ce140&section=Latest%20Jobs', lastDate: '', icon: 'fa-train', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Admit Cards' },
    { title: 'Indian Army Agniveer Rally Admit Card 2026', dept: 'Indian Army', qual: '10th / 12th Pass', state: 'All India', cat: 'Admit Card', tags: 'Indian Army Agniveer Rally Admit Card 2026 Join Indian Army Rally Recruiting Year 2027 Agniveer GD Technical army agniveer admit card rally 2026 sarkari naukri 2026', slug: 'job.html?slug=sr_admit_card-indian-army-agniveer-rally-admit-card-2026-619d4b&section=Latest%20Jobs', lastDate: '', icon: 'fa-star', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Admit Cards' },
    { title: 'Haryana HPSC Civil Services HCS Pre Result 2026 for 102 Post', dept: 'Haryana PSC', qual: 'Graduation', state: 'Haryana', cat: 'Result', tags: 'Haryana HPSC Civil Services HCS Pre Result 2026 for 102 Post Haryana Public Service Commission HPSC HCS Civil Services haryana hpsc hcs result 2026 sarkari naukri 2026', slug: 'job.html?slug=sr_result-haryana-hpsc-civil-services-hcs-pre-result-2026-for-102-post-01cfcf&section=Latest%20Jobs', lastDate: '', icon: 'fa-location-dot', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Results' },
    { title: 'SSC Combined Hindi Translators JHT Online Form 2026 for 84 Post', dept: 'Staff Selection Commission', qual: 'Post Graduation Hindi', state: 'All India', cat: 'Latest Job', tags: 'SSC Combined Hindi Translators JHT Online Form 2026 for 84 Post Staff Selection Commission SSC Combined Hindi Translators Junior Senior ssc jht hindi translator 84 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-ssc-combined-hindi-translators-jht-online-form-2026-for-84-post-ca7928&section=Latest%20Jobs', lastDate: '2026-05-14', icon: 'fa-medal', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
    // ✅ BPSSC entries - Bihar Police
    { title: 'BPSSC Bihar Police Sub Inspector SI Mains Admit Card 2026', dept: 'Bihar Police BPSSC', qual: 'Graduation', state: 'Bihar', cat: 'Admit Card', tags: 'BPSSC Bihar Police Sub Inspector SI Mains Admit Card 2026 Bihar Police Subordinate Services Commission BPSSC Sub Inspector SI bpssc bihar police sub inspector admit card 2026 sarkari naukri 2026', slug: 'job.html?slug=bpssc-bihar-police-sub-inspector-si-mains-admit-card-2026', lastDate: '', icon: 'fa-shield-halved', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Admit Cards' },
    { title: 'BPSSC Bihar Police Sub Inspector SI Online Form 2025 for 1799 Post', dept: 'Bihar Police Subordinate Services Commission', qual: 'Graduation', state: 'Bihar', cat: 'Latest Job', tags: 'BPSSC Bihar Police Sub Inspector SI Online Form 2025 Bihar Police SI 1799 bpssc bihar police sub inspector si 2025 sarkari naukri police', slug: 'job.html?slug=bpssc-bihar-police-sub-inspector-si-online-form-2025-for-1799-post', lastDate: '', icon: 'fa-shield-halved', lastUpdated: '2025-10-26T00:00:00', sectionSource: 'Latest Jobs' },
    { title: 'BPSSC Havildar Instructor Online Form 2026 for 122 Post', dept: 'Bihar Police BPSSC', qual: '10+2', state: 'Bihar', cat: 'Latest Job', tags: 'BPSSC Havildar Instructor Online Form 2026 Bihar Police Subordinate Services Commission BPSSC Havildar Instructor bpssc havildar police 12th 122 sarkari naukri 2026', slug: 'job.html?slug=sr_latest_jobs-bpssc-havildar-instructor-online-form-2026-for-122-post-16100a&section=Latest%20Jobs', lastDate: '2026-06-01', icon: 'fa-shield-halved', lastUpdated: '2026-05-14T00:00:00', sectionSource: 'Latest Jobs' },
  ];

  /* ── STATE ──────────────────────────────────────────────── */
  let fuseInstance = null;
  let allData = [...SEED_DATA];
  let activeIndex = -1;
  let suggestItems = [];
  let currentFilters = { qual: '', state: '', cat: '', sort: 'latest' };
  let fuseLoaded = false;
  let jsonIndexReady = false;   // ✅ true after all JSON files loaded

  /* ── UTILS ──────────────────────────────────────────────── */
  function esc(s) {
    return String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  function debounce(fn, ms) {
    let t; return function (...a) { clearTimeout(t); t = setTimeout(() => fn.apply(this, a), ms); };
  }

  function highlight(text, query) {
    if (!query || !text) return esc(text);
    const words = query.trim().split(/\s+/).filter(w => w.length > 1);
    let result = esc(text);
    words.forEach(w => {
      const rx = new RegExp('(' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      result = result.replace(rx, '<mark class="srch-hl">$1</mark>');
    });
    return result;
  }

  /* ── RECENT SEARCHES ────────────────────────────────────── */
  function getRecent() {
    try { return JSON.parse(localStorage.getItem(CFG.recentKey) || '[]'); } catch { return []; }
  }
  function saveRecent(q) {
    if (!q || q.length < 2) return;
    let list = getRecent().filter(r => r.toLowerCase() !== q.toLowerCase());
    list.unshift(q);
    list = list.slice(0, CFG.maxRecent);
    try { localStorage.setItem(CFG.recentKey, JSON.stringify(list)); } catch {}
  }

  /* ── LOAD FUSE.JS DYNAMICALLY ───────────────────────────── */
  function loadFuse(cb) {
    if (window.Fuse) { cb(); return; }
    const s = document.createElement('script');
    s.src = CFG.fuseJs;
    s.onload = cb;
    s.onerror = cb; // gracefully fall back to built-in search
    document.head.appendChild(s);
  }

  function buildFuse(data) {
    if (!window.Fuse) return;
    fuseInstance = new window.Fuse(data, {
      keys: [
        { name: 'title',  weight: 0.45 },
        { name: 'tags',   weight: 0.20 },
        { name: 'cat',    weight: 0.10 },
        { name: 'dept',   weight: 0.08 },
        { name: 'state',  weight: 0.07 },
        { name: 'qual',   weight: 0.05 },
        { name: 'org',    weight: 0.05 },
      ],
      threshold: 0.5,          // ✅ FIX: 0.45→0.5, single word bhi match hoga
      includeScore: true,
      ignoreLocation: true,
      minMatchCharLength: 1,  // ✅ FIX: 1 word/char se bhi search ho
    });
    fuseLoaded = true;
  }

  
  /* ── LOAD JSON FILES ────────────────────────────────────── */
  /*
   * Uses EXACT same parsing as script.js + job.html — verified field names:
   *
   * merged_sarkari_data.json:
   *   .jobs[]                     → {title, slug, apply_mode, organization,
   *                                   important_dates:{last_date}}
   *   .sarkariresultshine_jobs[]  → {title, source_url, organization, last_date}
   *   .sarkariresult_categories   → {SR_Latest_Jobs:[{title,url}], ...}
   *
   * dailyupdates.json:
   *   .sections[]                 → {title, id, icon, items:[{name, url, slug, date}]}
   *
   * Complete_Jobs_Full_Data.json:
   *   {Railway_Jobs:[...], Bank_Jobs:[...], ...}
   *   Each item: {title, slug, organization, basic_details:{job_title,organization_name},
   *               important_dates:{last_date}, total_vacancy, apply_mode}
   */

  /* Category meta for Complete_Jobs_Full_Data.json keys */
  const COMPLETE_JOBS_META = {
    Latest_Notifications: { id:'Latest Notifications',   icon:'fa-bell',             qual:'',               cat:'Latest'     },
    '10TH_Pass':          { id:'10th Pass Jobs',          icon:'fa-graduation-cap',   qual:'10th Pass',      cat:'State Jobs' },
    '8TH_Pass':           { id:'8th Pass Jobs',           icon:'fa-book',             qual:'8th Pass',       cat:'State Jobs' },
    '12TH_Pass':          { id:'12th Pass Jobs',          icon:'fa-graduation-cap',   qual:'12th Pass',      cat:'State Jobs' },
    Diploma:              { id:'Diploma Jobs',            icon:'fa-scroll',           qual:'Diploma',        cat:'Others'     },
    ITI:                  { id:'ITI Jobs',                icon:'fa-tools',            qual:'ITI',            cat:'ITI Jobs'   },
    B_Tech_BE:            { id:'B.Tech Jobs',             icon:'fa-microchip',        qual:'B.Tech',         cat:'Engineering'},
    B_Com:                { id:'B.Com Jobs',              icon:'fa-chart-line',       qual:'B.Com',          cat:'Others'     },
    Any_Graduate:         { id:'Graduation Jobs',         icon:'fa-university',       qual:'Graduation',     cat:'Others'     },
    Any_Post_Graduate:    { id:'Post Graduation Jobs',    icon:'fa-user-tie',         qual:'Post Graduation',cat:'Others'     },
    Railway_Jobs:         { id:'Railway Jobs',            icon:'fa-train',            qual:'',               cat:'Railway'    },
    Police_Defence:       { id:'Police Jobs',             icon:'fa-shield-halved',    qual:'',               cat:'Police'     },
    Teaching_Faculty:     { id:'Teaching Jobs',           icon:'fa-chalkboard-user',  qual:'B.Ed',           cat:'Teaching'   },
    Bank_Jobs:            { id:'Bank Jobs',               icon:'fa-building-columns', qual:'Graduation',     cat:'Bank'       },
    Medical_Hospital:     { id:'Medical Jobs',            icon:'fa-stethoscope',      qual:'',               cat:'Medical'    },
    Last_Date_Reminder:   { id:'Last Date Reminder',      icon:'fa-clock',            qual:'',               cat:'Latest'     },
    SSC_Jobs:             { id:'SSC Jobs',                icon:'fa-medal',            qual:'',               cat:'SSC'        },
    UPSC_Jobs:            { id:'UPSC Jobs',               icon:'fa-graduation-cap',   qual:'Graduation',     cat:'UPSC'       },
    Haryana_Jobs:         { id:'Haryana Jobs',            icon:'fa-location-dot',     qual:'',               cat:'State Jobs' },
    Defence_Jobs:         { id:'Defence Jobs',            icon:'fa-star',             qual:'',               cat:'Defence'    },
  };

  /* Exact same slugify as script.js slugifyForJob */
  /* ── slugifyTitle: matches script.js's slugify() exactly ──
   * Used for Complete_Jobs_Full_Data.json, merged_sarkari_data.json,
   * and state-jobs-data.json so URLs are identical to what script.js generates.
   *
   * KEY DIFFERENCES from the old NFKD version:
   *  • '&' is removed (not converted to "and") — e.g. "Andaman & Nicobar" → "andaman-nicobar"
   *  • '/' is removed (not converted to "-") — e.g. "CEN 01/2026" → "cen-012026"
   *  • No NFKD normalisation (script.js doesn't use it)
   */
  function slugifyTitle(raw) {
    return String(raw || '')
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')   // keep only letters, digits, spaces, hyphens
      .replace(/[\s-]+/g, '-')         // collapse whitespace / hyphens → single '-'
      .slice(0, 120)
      .replace(/^-+|-+$/g, '') || 'official-link';
  }

  /* Build job.html href from a job object — same as index.html jobHref() */
  function buildJobHref(job, secId) {
    const bd = job.basic_details || {};
    const rawTitle = job.title || job.post_name ||
                     bd.job_title || bd.post_name || '';
    const slug = job.slug || slugifyTitle(rawTitle);
    if (!slug || slug === 'official-link') return job.source_url || job.url || job.link || '#';
    // Check apply_mode at top level AND inside basic_details.application_mode
    const applyMode = (job.apply_mode || bd.application_mode || '').toLowerCase();
    const prefix = applyMode === 'offline' ? 'offline-' : '';
    return 'job.html?slug=' + encodeURIComponent(prefix + slug) +
           (secId ? '&section=' + encodeURIComponent(secId) : '');
  }

  /* Extract title from a job object — same priority as job.html parseFullJob
   * Handles all 3 JSON formats:
   *   merged_sarkari_data.json  → job.title  (e.g. "Ambala Court Clerk Vacancy 2026")
   *   Complete_Jobs_Full_Data.json → basic_details.job_title
   *   dailyupdates.json items   → item.name  (handled in section loop directly)
   */
  function getJobTitle(job) {
    const bd = job.basic_details || {};
    const raw = String(
      job.title || job.post_name ||
      bd.job_title || bd.post_name ||
      job.name || ''
    ).trim();
    // Strip trailing punctuation/dashes left by scrapers (e.g. "Apply Now -")
    return raw.replace(/[\s\-–—,|]+$/, '').trim();
  }

  /* Extract org from a job object */
  function getJobOrg(job) {
    const bd = job.basic_details || {};
    return String(
      job.organization || job.board_name || job.department ||
      bd.organization_name || bd.department || ''
    ).trim();
  }

  /* ── SHARED DEDUP KEY ──────────────────────────────────── */
  function dedupeKey(slug) {
    if (!slug) return slug;
    try {
      const u = new URL(slug, 'https://x.com');
      const s = u.searchParams.get('slug') || u.pathname;
      return s.toLowerCase().trim();
    } catch (_) {
      return slug.split('?')[0].toLowerCase().trim();
    }
  }

  /* ══════════════════════════════════════════════════════════════
   * GLOBAL ITEM VALIDATOR
   * Runs on EVERY item from EVERY JSON file before it enters allData.
   * Blocks: nav/category links, tools, external non-job URLs, garbage.
   * ══════════════════════════════════════════════════════════════ */
  function isValidJobItem(item) {
    const title = (item.title || '').trim();
    const slug  = (item.slug  || '').trim();

    // 1. Title must exist and be meaningful
    if (!title || title.length < 5) return false;

    // 2. Must have a URL
    if (!slug || slug === '#') return false;

    // 3. Block pure nav/category labels like "SSC Jobs", "BSC Jobs", "Assam", "Manipur"
    const navLabelRx = /^(ssc|bsc|msc|ba|bca|bba|mca|mba|iti|diploma|b\.?tech|be|railway|police|bank|army|navy|air force|upsc|bpsc|hpsc|rpsc|mpsc|tnpsc|sarkari|central|defence|teaching|medical|haryana|punjab|rajasthan|uttar pradesh|up|bihar|gujarat|maharashtra|assam|manipur|sikkim|himachal|himachal pradesh|meghalaya|tripura|nagaland|arunachal|mizoram|jharkhand|chhattisgarh|uttarakhand|odisha|telangana|andhra|karnataka|kerala|west bengal|goa|delhi|jammu|ladakh|chandigarh|mp|hp|assistant)\s*(jobs?|pass|result|admit card|vacancy|bharti|naukri|recruitment|exam|form|notification|updates?|news)?$/i;
    if (navLabelRx.test(title.trim())) return false;

    // 4. Block titles that are ONLY a state/region name
    const LONE_STATES = new Set(['assam','manipur','sikkim','meghalaya','tripura','nagaland','mizoram','goa','himachal','uttarakhand','chhattisgarh','jharkhand','telangana','odisha','maharashtra','gujarat','punjab','haryana','bihar','rajasthan']);
    if (LONE_STATES.has(title.toLowerCase().trim())) return false;

    // 5. Block non-job content by title keywords
    // FIX: \b removed for Hindi-mixed titles — e.g. 'लाडो लक्ष्मी Yojana' mein \b kaam nahi karta
    const titleLower = title.toLowerCase();

    // 5a. Keyword list check (includes() — works for Hindi+English mixed text)
    const NON_JOB_KW = [
      'yojana','yojna','scheme','subsidy','e-kyc','ekyc','ration card',
      'pan apply','pan link','pan card','e-pan','epan','nsdl pan','uti pan',
      'tractor','draw list','dairy farming','pashu','mahostav',
      'solar pump','solar water','refund','housing ews','land holding',
      'sc farmer','domicile','certificate download',
      'image resizer','image quality','pdf tool','video compress',
      'mp4 to','photo edit','qr code','word to','compress image',
      'convert image','ebook','e-book','helpdesk',
      'study material','current affairs','answer key','syllabus',
      'cut off','mock test','jagran','ndtv','amar ujala','dainik bhaskar',
      'apply link','apply apply','application download','application link',
      'seed subsidy','dhaincha','face rd','aadhaar face',
      'laxmi','ladli','laado','laadli','laddo',
    ];
    for (const kw of NON_JOB_KW) {
      if (titleLower.includes(kw)) return false;
    }

    // 5b. Block items from non-job sections — check ALL possible section fields
    const nonJobSection = /importantcsc|csc.?(pdf|link)|govt.?scheme|yojana|yojna|khabar|latest.?khabar|study.?material|current.?affair|employment.?news|apply.?link/i;
    const itemSec = String(item.sectionSource || '') + '|' + String(item.dept || '') + '|' + String(item.cat || '');
    if (nonJobSection.test(itemSec)) return false;

    // 5c. Block 'Apply Link' or 'Apply APPLY' pattern (CSC link items)
    if (/apply\s+(link|apply)/i.test(title)) return false;
    // 6. Block external URLs that are clearly NOT job detail pages
    //    Internal pages: job.html?slug=... — ALWAYS allow
    //    External URLs: allow only if they look like a job page (not tools/image/pdf)
    if (/^https?:\/\//i.test(slug)) {
      // Block obvious non-job external pages
      if (/image|photo|compress|convert|pdf.?tool|video|mp4|qr.?code|resizer|watermark/i.test(slug)) return false;
      // Allow job-like external pages (freejobalert, sarkariresult, etc.)
      // These come from dailyupdates.json sections with real job listings
    }

    // 7. Block internal nav/category page links
    if (/\/(tools|govt-services|category|state-jobs\.html|about|contact|index\.html?)(\?|$)/i.test(slug)) return false;

    // 8. Block view.html?section=... links — these are category pages not job pages
    if (/^view\.html\?section=/i.test(slug)) return false;

    // 9. Short titles (<20 chars) must contain a job-posting keyword
    if (title.length < 20) {
      const hasJobKeyword = /\b(20[0-9]{2}|post|form|result|admit|vacancy|bharti|recruitment|exam|notification|online|offline|apply)\b/i.test(title);
      if (!hasJobKeyword) return false;
    }

    return true;
  }

  /* ── MERGE BATCH INTO allData (deduplicated) ────────────── */
  function mergeItems(extra, totalLoaded) {
    if (!extra.length) return;
    const seen = new Set(allData.map(d => dedupeKey(d.slug)));
    // Run global validator on every item before merging
    const valid = extra.filter(item => isValidJobItem(item));
    const blocked = extra.length - valid.length;
    if (blocked > 0) console.log('[smart-search] Blocked', blocked, 'non-job items from index.');
    valid.forEach(item => {
      const key = dedupeKey(item.slug);
      if (!seen.has(key)) {
        seen.add(key);
        // ✅ FIX: Ensure lastUpdated is always set — fallback to now so new items sort to top
        if (!item.lastUpdated) item.lastUpdated = new Date().toISOString();
        allData.push(item);
      }
    });
    // ✅ FIX: Sort allData so newest items always at top
    allData.sort((a, b) => {
      const ta = a.lastUpdated ? new Date(a.lastUpdated).getTime() : 0;
      const tb = b.lastUpdated ? new Date(b.lastUpdated).getTime() : 0;
      return tb - ta;
    });
    // Refresh any active heroSearch with updated data
    loadFuse(() => {
      buildFuse(allData);
      const heroInput = document.getElementById('heroSearch');
      if (heroInput && heroInput.value.trim().length >= 1) {
        heroInput.dispatchEvent(new Event('input'));
      }
    });
    console.log('[smart-search] Merged', totalLoaded, 'items. allData total:', allData.length);
  }

  /* ── PROCESS ONE JSON FILE ──────────────────────────────── */
  function processJsonFile(data, fileName) {
    const extra = [];
    let count = 0;

      /* ══════════════════════════════════════════════════════
         1.  merged_sarkari_data.json
         Structure: { jobs:[] }
         Each job: { title, post_name, organization, apply_mode,
                     important_dates:{application_start, last_date},
                     total_vacancy, official_website_link }
         NOTE: No 'slug' field — href is built by slugifying title.
      ══════════════════════════════════════════════════════ */
      if (fileName === 'merged_sarkari_data.json') {

        /* jobs[] — main array */
        const mainJobs = Array.isArray(data.jobs) ? data.jobs : [];
        mainJobs.forEach(j => {
          const title = getJobTitle(j);
          if (!title) return;
          const org  = getJobOrg(j);
          const href = buildJobHref(j, 'Latest Jobs');
          if (!href || href === '#') return;
          const lastDate = (j.important_dates
            ? (j.important_dates.last_date || j.important_dates.last_date_to_apply || '')
            : '') || j.last_date || '';
          const applyMode = (j.apply_mode || '').toLowerCase();
          // Rich tags: include short_information (org naam wahan hota hai) + eligibility
          const shortInfo  = String(j.short_information || '').slice(0, 200);
          const eligibility = String(j.eligibility || '').slice(0, 100);
          const category    = String(j.category || '').toLowerCase().replace(/_/g,' ');
          extra.push({
            title, slug: href,
            dept: org || shortInfo.slice(0, 80),   // fallback: short_info se org naam
            qual: j.qualification || eligibility || '',
            state: j.job_location || j.state || 'All India',
            cat: applyMode === 'offline' ? 'Offline Form' : 'Latest Job',
            tags: title + ' ' + org + ' ' + (j.post_name || '') + ' '
                + String(j.total_vacancy || j.total_post || '') + ' '
                + shortInfo + ' ' + eligibility + ' ' + category
                + ' sarkari naukri 2026',
            lastDate,
            icon: 'fa-briefcase',
            lastUpdated: (() => {
              // Priority: updated_at > last_updated > post_date > now
              if (j.updated_at) return j.updated_at;
              if (j.last_updated) return j.last_updated;
              if (j.post_date) return j.post_date + 'T00:00:00';
              // Fallback: use last_date as proxy for recency (recent deadline = recent posting)
              if (lastDate && /\d{4}-\d{2}-\d{2}/.test(lastDate)) return lastDate + 'T00:00:00';
              return new Date().toISOString();
            })(),
            sectionSource: 'Latest Jobs',
          });
          count++;
        });

        /* sarkariresultshine_jobs[] — if present in future updates */
        if (Array.isArray(data.sarkariresultshine_jobs)) {
          data.sarkariresultshine_jobs.forEach(j => {
            const title = getJobTitle(j);
            if (!title) return;
            const org  = getJobOrg(j);
            const href = j.source_url || j.url || j.link || buildJobHref(j, 'SR Latest Jobs');
            if (!href || href === '#') return;
            const lastDate = (j.important_dates
              ? (j.important_dates.last_date || '')
              : '') || j.last_date || '';
            extra.push({
              title, slug: href,
              dept: org,
              qual: '', state: '',
              cat: 'Latest Job',
              tags: title + ' ' + org + ' sarkari result naukri',
              lastDate,
              icon: 'fa-briefcase',
              lastUpdated: j.updated_at || new Date().toISOString(),
              sectionSource: 'Sarkari Result',
            });
            count++;
          });
        }

        /* sarkariresult_categories — if present in future updates */
        const srCats = data.sarkariresult_categories || {};
        const SR_META = {
          SR_Latest_Jobs: { cat:'Latest Job',  icon:'fa-briefcase',      label:'SR Latest Jobs' },
          SR_Admit_Card:  { cat:'Admit Card',  icon:'fa-id-card',        label:'SR Admit Card'  },
          SR_Result:      { cat:'Result',      icon:'fa-trophy',         label:'SR Result'      },
          SR_Admission:   { cat:'Admission',   icon:'fa-graduation-cap', label:'SR Admission'   },
          SR_Answer_Key:  { cat:'Answer Key',  icon:'fa-key',            label:'SR Answer Key'  },
        };
        Object.keys(srCats).forEach(key => {
          const m   = SR_META[key] || { cat: key, icon: 'fa-circle-dot', label: key };
          const arr = Array.isArray(srCats[key]) ? srCats[key] : [];
          arr.forEach(item => {
            const title = String(item.title || item.name || '').trim();
            const href  = item.url || item.link || item.source_url || '';
            if (!title || !href) return;
            extra.push({
              title, slug: href,
              dept: item.org || item.organization || '',
              qual: '', state: '',
              cat: m.cat,
              tags: title + ' ' + m.cat + ' sarkari result 2026',
              lastDate: item.last_date || '',
              icon: m.icon,
              lastUpdated: item.updated_at || new Date().toISOString(),
              sectionSource: m.label,
            });
            count++;
          });
        });
      }

      /* ══════════════════════════════════════════════════════
         2.  dailyupdates.json
         Structure: { sections:[{id, title, icon, items:[{name, url, slug}]}] }
         
         IMPORTANT: Only "TOP Headlines Today" section has real internal job links.
         All other sections (Govt Scheme, ImportantCSC PDF, ImportantCSC link,
         Top 20 Jobs, Today Updates) are 100% external URLs (freejobalert, jagran, 
         pdfdrive etc.) — these must be SKIPPED entirely.
      ══════════════════════════════════════════════════════ */
      if (fileName === 'dailyupdates.json') {
        const sections = Array.isArray(data.sections) ? data.sections
          : Array.isArray(data) ? data : [];

        /* BLACKLIST: These non-job sections are always skipped.
         * Baki SABHI sections allowed hain — jobs, admit cards, results, headlines sab.
         * Pehle ka strict whitelist hata diya — isse dailyupdates.json ke results
         * search mein nahi aa rahe the. */
        const BLOCKED_SECTIONS = new Set([
          'importantcsc pdf',
          'importantcsc link',
          'important csc pdf',
          'important csc link',
          'csc pdf',
          'govt scheme',
          'govt schemes',
          'government scheme',
          'yojana',
          'yojna',
          'khabar',
          'latest khabar',
          'study material',
          'current affairs',
          'employment news',
          'international news',
          'world news',
        ]);

        sections.forEach(sec => {
          const secTitle = String(sec.title || sec.id || '').trim();
          const secTitleLower = secTitle.toLowerCase();

          // SKIP only blocked non-job sections
          if (BLOCKED_SECTIONS.has(secTitleLower)) {
            console.log('[smart-search] dailyupdates: Skipping blocked section:', secTitle);
            return;
          }
          // Also skip if section title matches non-job pattern
          if (/csc.?(pdf|link)|govt.?scheme|yojana|yojna|khabar|study.?material|current.?affair|employment.?news|international.?news/i.test(secTitle)) {
            console.log('[smart-search] dailyupdates: Skipping non-job section:', secTitle);
            return;
          }

          const secId   = String(sec.id || sec.title || '').trim();
          const secIcon = (String(sec.icon || 'fa-bell')).replace(/^fa-solid\s+/, '');

          (sec.items || []).forEach(item => {
            const title = String(item.name || item.title || '').trim();
            if (!title) return;

            /* Build href: internal slug preferred, then relative URL, then external */
            let href = '';
            if (item.slug) {
              href = 'job.html?slug=' + encodeURIComponent(item.slug)
                   + '&section=' + encodeURIComponent(secId || secTitle);
            } else if (item.url && !item.url.startsWith('http')) {
              href = item.url; // relative internal URL
            } else if (item.url) {
              href = item.url; // external URL — allowed for job pages
            } else if (item.link) {
              href = item.link;
            }
            // Skip if no link found at all
            if (!href) return;

            const duDate = item.date || item.lastDate || item.last_date || '';
            
            // ✅ FIX: lastUpdated — dailyupdates items are NEWEST data, so give them
            // a very fresh timestamp so they appear at TOP in results.
            // Priority: item.updated_at > item.postDate > item.date > section date > NOW
            let duUpdated;
            if (item.updated_at) {
              duUpdated = item.updated_at;
            } else if (item.postDate) {
              // postDate format: "DD/MM/YYYY" → convert to ISO
              const pd = String(item.postDate).split('/');
              if (pd.length === 3) duUpdated = `${pd[2]}-${pd[1]}-${pd[0]}T00:00:00`;
              else duUpdated = new Date().toISOString();
            } else if (duDate && /\d{4}-\d{2}-\d{2}/.test(duDate)) {
              duUpdated = duDate + 'T00:00:00';
            } else {
              // No date info → treat as today (newest)
              duUpdated = new Date().toISOString();
            }

            // Determine category from section title
            const catFromSec = /result/i.test(secTitle) ? 'Result'
              : /admit.?card/i.test(secTitle) ? 'Admit Card'
              : /answer.?key/i.test(secTitle) ? 'Answer Key'
              : /admission/i.test(secTitle) ? 'Admission'
              : 'Latest Job';

            extra.push({
              title, slug: href,
              dept: String(item.board || item.organization || item.dept || secTitle).trim(),
              qual: String(item.qualification || '').trim(),
              state: String(item.state || 'All India').trim(),
              cat: catFromSec,
              tags: title + ' ' + secTitle + ' ' + (item.board || '') + ' sarkari naukri 2026',
              lastDate: duDate,
              icon: secIcon || 'fa-bell',
              lastUpdated: duUpdated,
              sectionSource: secTitle,
            });
            count++;
          });
        });
      }

      /* ══════════════════════════════════════════════════════
         3.  Complete_Jobs_Full_Data.json
         Structure: { Railway_Jobs:[...], Bank_Jobs:[...], ... }
         Each item: { title, slug, organization, apply_mode,
                      basic_details:{job_title, organization_name},
                      important_dates:{last_date, last_date_to_apply} }
         (verified from job.html parseFullJob + _JOBS_CAT_META_JI)
      ══════════════════════════════════════════════════════ */
      if (fileName === 'Complete_Jobs_Full_Data.json') {
        if (data && typeof data === 'object' && !Array.isArray(data)) {

          /* Handle known category keys first */
          const handledKeys = new Set(Object.keys(COMPLETE_JOBS_META));

          /* Process known categories */
          Object.entries(COMPLETE_JOBS_META).forEach(([catKey, meta]) => {
            const jobs = Array.isArray(data[catKey]) ? data[catKey] : [];
            jobs.forEach(job => {
              const title = getJobTitle(job);
              if (!title) return;
              const org  = getJobOrg(job);
              const bd   = job.basic_details || {};
              const href = buildJobHref(job, meta.id);
              const dates = job.important_dates || {};
              const lastDate = (
                dates.last_date_to_apply || dates.last_date ||
                dates.closing_date || job.last_date || ''
              ).toString().trim();
              // Include post_name + short_information in tags for richer search
              const postName = String(bd.post_name || job.post_name || '').trim();
              const shortInfo = String(bd.short_information || '').slice(0, 100);
              extra.push({
                title, slug: href,
                dept: org,
                qual: meta.qual || job.qualification || bd.qualification || '',
                state: job.state || 'All India',
                cat: meta.cat,
                tags: title + ' ' + postName + ' ' + org + ' ' + meta.id
                    + ' ' + (job.total_vacancies || job.total_vacancy || bd.total_vacancies || '')
                    + ' ' + shortInfo + ' sarkari job 2026',
                lastDate,
                icon: meta.icon,
                lastUpdated: bd.last_updated || job.updated_at || job.last_updated || job.created_at || new Date().toISOString(),
                sectionSource: meta.id,
              });
              count++;
            });
          });

          /* Process any remaining unknown keys */
          Object.keys(data).forEach(key => {
            if (handledKeys.has(key)) return;
            const arr = Array.isArray(data[key]) ? data[key] : [];
            arr.forEach(job => {
              const title = getJobTitle(job);
              if (!title) return;
              const org  = getJobOrg(job);
              const label = key.replace(/_/g, ' ');
              const href  = buildJobHref(job, label);
              const dates = job.important_dates || {};
              const lastDate = (
                dates.last_date_to_apply || dates.last_date ||
                dates.closing_date || job.last_date || ''
              ).toString().trim();
              extra.push({
                title, slug: href,
                dept: org,
                qual: job.qualification || '',
                state: job.state || 'All India',
                cat: label,
                tags: title + ' ' + org + ' ' + label + ' sarkari naukri',
                lastDate,
                icon: 'fa-briefcase',
                lastUpdated: job.updated_at || job.last_updated || new Date().toISOString(),
                sectionSource: label,
              });
              count++;
            });
          });
        }
      }

      /* ══════════════════════════════════════════════════════
         4.  state-jobs-data.json
         Structure: { sections:[{id, title, state, items:[{name, url, date,
                      lastDate, qualification, board, detail}]}] }
         Rich items with qualification, board, detail.basic_details, seo_tags.
      ══════════════════════════════════════════════════════ */
      if (fileName === 'state-jobs-data.json') {
        const sections = Array.isArray(data.sections) ? data.sections
          : Array.isArray(data) ? data : [];

        sections.forEach(sec => {
          const secId    = String(sec.id    || sec.title || '').trim();
          const secTitle = String(sec.title || sec.id    || 'State Jobs').trim();
          const secState = String(sec.state || '').trim();

          (sec.items || []).forEach(item => {
            const title = String(item.name || item.title || '').trim();
            if (!title) return;

            /* href: prefer internal slug from detail, else direct url */
            const detail    = item.detail || {};
            const bd        = detail.basic_details || {};
            const applyMode = (bd.application_mode || '').toLowerCase();
            let href = item.url || item.link || '';

            /* Try to build job.html link using slugified title */
            const slug = slugifyTitle(bd.job_title || title);
            if (slug && slug !== 'official-link') {
              const prefix = applyMode.includes('offline') ? 'offline-' : '';
              href = 'job.html?slug=' + encodeURIComponent(prefix + slug)
                   + '&section=' + encodeURIComponent(secId || secTitle);
            }
            if (!href) return;

            /* Extract qualification — item level OR detail level */
            const qual = String(
              item.qualification ||
              (detail.qualification && (detail.qualification.education_qualification || '')) ||
              bd.qualification || ''
            ).trim();

            /* Build rich tags including seo_tags array if present */
            const seoTags = Array.isArray(detail.seo_tags)
              ? detail.seo_tags.join(' ') : '';
            const shortInfo = String(bd.short_information || '').slice(0, 120);
            const board = String(item.board || bd.organization_name || '').trim();
            const tags = [
              title, board, secTitle, secState, qual,
              seoTags, shortInfo, 'state jobs sarkari naukri 2026',
            ].filter(Boolean).join(' ');

            /* Last date */
            const dates = detail.important_dates || {};
            const lastDate = String(
              item.lastDate || item.date ||
              dates.last_date_to_apply || dates.last_date ||
              dates.closing_date || ''
            ).replace(/^Last Date:\s*/i, '').trim();

            extra.push({
              title, slug: href,
              dept: board || secTitle,
              org:  board,
              qual,
              state: secState || 'All India',
              cat: 'State Jobs',
              tags,
              lastDate,
              icon: 'fa-location-dot',
              lastUpdated: item.postDate
                ? new Date(item.postDate.split('/').reverse().join('-')).toISOString()
                : new Date().toISOString(),
              sectionSource: secTitle,
            });
            count++;
          });
        });
      }

    return { extra, count };
  }

  /* ── FETCH + INDEX HELPER ───────────────────────────────── */
  function fetchAndIndex(fileName) {
    return fetch(fileName)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        const { extra, count } = processJsonFile(data, fileName);
        console.log('[smart-search]', fileName, '→', count, 'items');
        mergeItems(extra, count);
        return count;
      })
      .catch(err => {
        console.warn('[smart-search] Failed to load:', fileName, err);
        return 0;
      });
  }

  /* ── LOAD JSON FILES — streaming, not all-at-once ───────── */
  /*
   * KEY FIX: Previously used Promise.allSettled() which waited for ALL files
   * including the 11MB Complete_Jobs_Full_Data.json before setting
   * jsonIndexReady=true. This caused 10-30s delay on slow connections.
   *
   * NEW APPROACH:
   *  Phase 1 — Fast files (merged_sarkari + dailyupdates, ~700KB total):
   *            Load together, set jsonIndexReady=true immediately after.
   *            Search works within ~1-2 seconds.
   *  Phase 2 — Heavy file (Complete_Jobs_Full_Data.json, 11MB):
   *            Loads in background, merges silently, refreshes active search.
   */
  function loadJsonFiles() {
    /*
     * LOADING STRATEGY v4.0 — ONLY 4 SOURCE JSON FILES
     *
     * jobs-search-index.json is SKIPPED entirely (it had wrong/stale data).
     * All search data comes ONLY from these 4 authoritative JSON files:
     *
     * Phase 1 (FAST) — merged_sarkari_data.json + dailyupdates.json
     *   ~700KB total, loads in ~1s. Sets jsonIndexReady=true so search is live.
     *
     * Phase 2 (MEDIUM) — state-jobs-data.json
     *   Loads in background after Phase 1 is ready.
     *
     * Phase 3 (HEAVY) — Complete_Jobs_Full_Data.json (~11MB)
     *   Loads in background after 2s delay. Merges silently into allData.
     */

    // Phase 1: FASTEST — dailyupdates.json FIRST (freshest data, ~50KB)
    // Yeh file sabse chhoti aur sabse fresh hai — pehle load hogi taaki
    // latest jobs search results mein sabse upar dikhein.
    fetchAndIndex('dailyupdates.json').then(() => {
      console.log('[smart-search] ⚡ dailyupdates loaded first. allData:', allData.length);
      jsonIndexReady = true;
      loadFuse(() => {
        buildFuse(allData);
        const heroInput = document.getElementById('heroSearch');
        if (heroInput && heroInput.value.trim().length >= 1) {
          heroInput.dispatchEvent(new Event('input'));
        }
      });

      // Phase 2: merged_sarkari_data.json (~600KB)
      fetchAndIndex('merged_sarkari_data.json').then(() => {
        console.log('[smart-search] ✅ Phase 2 done (merged_sarkari). Total:', allData.length);
        loadFuse(() => {
          buildFuse(allData);
          const heroInput = document.getElementById('heroSearch');
          if (heroInput && heroInput.value.trim().length >= 1) {
            heroInput.dispatchEvent(new Event('input'));
          }
        });

        // Phase 3: state-jobs-data.json — loads after Phase 2
        fetchAndIndex('state-jobs-data.json').then(() => {
          console.log('[smart-search] ✅ Phase 3 done (state-jobs). Total:', allData.length);
          if (typeof buildFuse === 'function') buildFuse(allData);
        });
      });
    });

    // Phase 3: Complete_Jobs_Full_Data.json — heavy file, background after 2s
    setTimeout(() => {
      fetchAndIndex('Complete_Jobs_Full_Data.json').then(() => {
        console.log('[smart-search] \u2705 Phase 3 done (Complete_Jobs). Total:', allData.length);
        if (typeof buildFuse === 'function') buildFuse(allData);
        const heroInput = document.getElementById('heroSearch');
        if (heroInput && heroInput.value.trim().length >= 1) {
          heroInput.dispatchEvent(new Event('input'));
        }
      });
    }, 2000);
  }

    /* ── SORT BY LAST UPDATED (descending) ─────────────────── */
  function sortByLastUpdated(results) {
    return results.slice().sort((a, b) => {
      const ta = a.lastUpdated ? new Date(a.lastUpdated).getTime() : 0;
      const tb = b.lastUpdated ? new Date(b.lastUpdated).getTime() : 0;
      return tb - ta; // newest first
    });
  }

  /* ── FORMAT RELATIVE TIME ───────────────────────────────── */
  function relativeTime(dateStr) {
    if (!dateStr) return null;
    const d = new Date(dateStr);
    if (isNaN(d)) return null;
    const now = Date.now();
    const diff = now - d.getTime();
    const mins  = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days  = Math.floor(diff / 86400000);
    if (mins < 1)   return 'अभी';
    if (mins < 60)  return `${mins} मिनट पहले`;
    if (hours < 24) return `${hours} घंटे पहले`;
    if (days < 7)   return `${days} दिन पहले`;
    return d.toLocaleDateString('hi-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  /* ── STOP WORDS — common words jo score inflate karte hain ── */
  const STOP_WORDS = new Set([
    'recruitment','2026','2025','2024','apply','online','offline','now','out',
    'notification','for','and','the','of','to','in','a','an','is','are','with',
    'posts','post','grade','form','exam','test','board','india','all','bharti',
    'vacancy','vacancies','jobs','job','latest','new','official','download',
  ]);

  /* ── CUSTOM SCORER — title match ko priority de ─────────── */
  function scoreItem(item, q, queryWords, meaningfulWords) {
    const title = (item.title || '').toLowerCase();
    const tags  = (item.tags  || '').toLowerCase();
    const cat   = (item.cat   || '').toLowerCase();
    const dept  = (item.dept  || '').toLowerCase();
    const sec   = (item.sectionSource || '').toLowerCase();
    const org   = (item.org   || item.dept || '').toLowerCase();
    const state = (item.state || '').toLowerCase();
    const qual  = (item.qual  || '').toLowerCase();
    let score = 0;

    // Tier 1: exact full query in title
    if (title.includes(q)) score += 200;
    else if (queryWords.length > 0 && title.startsWith(queryWords[0])) score += 80;

    // Tier 2: meaningful words in title
    let titleMeaningfulHits = 0;
    meaningfulWords.forEach(w => {
      if (title.includes(w)) {
        score += w.length >= 5 ? 40 : (w.length >= 3 ? 20 : 8);
        titleMeaningfulHits++;
      }
    });
    // Bonus: ALL meaningful words found in title
    if (meaningfulWords.length > 0 && titleMeaningfulHits === meaningfulWords.length) score += 60;

    // Tier 3: meaningful words in tags/dept/cat/sec/org/state/qual
    // ✅ FIXED: Higher weights for tags (rich data source)
    meaningfulWords.forEach(w => {
      if (tags.includes(w))  score += w.length >= 5 ? 15 : 8;  // increased
      if (cat.includes(w))   score += 8;
      if (dept.includes(w))  score += 8;  // increased
      if (sec.includes(w))   score += 6;
      if (org.includes(w))   score += 8;  // increased
      if (state.includes(w)) score += 7;
      if (qual.includes(w))  score += 5;
    });

    // Tier 4: ALL query words (inc stop words) match in title
    let allWordsHit = 0;
    queryWords.forEach(w => { if (title.includes(w)) allWordsHit++; });
    if (allWordsHit === queryWords.length && queryWords.length >= 2) score += 50;

    // ✅ NEW Tier 4b: Partial match - even 1 meaningful word in title/tags gives score
    // Handles "BPSSC Bihar Police Sub Inspector" when only "bpssc" or "bihar" matches
    if (titleMeaningfulHits === 0 && meaningfulWords.length > 0) {
      let anyTagHit = 0;
      meaningfulWords.forEach(w => {
        if (tags.includes(w)) anyTagHit++;
      });
      if (anyTagHit >= 1) score += anyTagHit * 8; // low score, will show after title matches
    }

    // ✅ NEW: Partial title match bonus - if >=1 meaningful word in title
    if (titleMeaningfulHits >= 1 && titleMeaningfulHits < meaningfulWords.length) {
      score += 10; // partial match bonus
    }

    // Penalty: only stop words matched AND no tag hits
    if (titleMeaningfulHits === 0 && score > 0 && score < 20) score = Math.floor(score * 0.4);

    // ✅ FIX: Freshness bonus — items updated in last 3 days get score boost so they surface on top
    if (score > 0 && item.lastUpdated) {
      const diffDays = (Date.now() - new Date(item.lastUpdated).getTime()) / 86400000;
      if (diffDays <= 1) score += 30;       // today/yesterday → +30
      else if (diffDays <= 3) score += 15;  // 2-3 days → +15
      else if (diffDays <= 7) score += 5;   // this week → +5
    }

    return score;
  }

  /* ── SEARCH ENGINE ──────────────────────────────────────── */
  function doSearch(query, filters = {}) {
    const q = (query || '').trim().toLowerCase();
    if (!q) return [];

    const queryWords      = q.split(/\s+/).filter(w => w.length >= 1);
    const meaningfulWords = queryWords.filter(w => w.length >= 2 && !STOP_WORDS.has(w));

    // MIN_SCORE: ✅ FIXED - partial word matches bhi dikhao
    // "BPSSC Bihar Police Sub Inspector" => agar koi bhi meaningful word mile toh show karo
    // jsonIndexReady = false ho toh aur bhi loose rakho
    const MIN_SCORE = jsonIndexReady ? 8 : 3;

    let results = allData
      .map(item => {
        const s = scoreItem(item, q, queryWords, meaningfulWords);
        return s >= MIN_SCORE ? { ...item, _score: s } : null;
      })
      .filter(Boolean)
      .sort((a, b) => {
        // Primary: score descending
        if (b._score !== a._score) return b._score - a._score;
        // Secondary: lastUpdated descending (newest data upar)
        const ta = a.lastUpdated ? new Date(a.lastUpdated).getTime() : 0;
        const tb = b.lastUpdated ? new Date(b.lastUpdated).getTime() : 0;
        if (tb !== ta) return tb - ta;
        // Tertiary: lastDate descending (upcoming deadlines upar)
        const da = a.lastDate ? new Date(a.lastDate).getTime() : 0;
        const db = b.lastDate ? new Date(b.lastDate).getTime() : 0;
        return db - da;
      });

    // Apply filters
    if (filters.qual)  results = results.filter(r => (r.qual  || '').toLowerCase().includes(filters.qual.toLowerCase()));
    if (filters.state) results = results.filter(r => {
      const rs = (r.state || '').toLowerCase();
      return rs === 'all india' || rs.includes(filters.state.toLowerCase());
    });
    if (filters.cat)   results = results.filter(r => (r.cat   || '').toLowerCase().includes(filters.cat.toLowerCase()));

    return results;
  }

  /* ── RENDER SUGGESTION ITEM ─────────────────────────────── */
  function renderSuggestItem(item, query, idx) {
    // Build meta line: Section · Dept · State
    const metaParts = [];
    if (item.sectionSource) metaParts.push(esc(item.sectionSource));
    else if (item.cat)      metaParts.push(esc(item.cat));
    if (item.dept && item.dept !== item.sectionSource) metaParts.push(esc(item.dept));
    if (item.state && item.state !== 'All India') metaParts.push(esc(item.state));
    const meta = metaParts.join(' · ');

    return `
      <a class="tsj-suggest-item${idx === activeIndex ? ' tsj-active' : ''}" 
         href="${esc(item.slug)}" 
         data-idx="${idx}" 
         role="option"
         aria-selected="${idx === activeIndex}">
        <span class="tsj-si-icon"><i class="fa-solid ${esc(item.icon || 'fa-briefcase')}"></i></span>
        <span class="tsj-si-body">
          <span class="tsj-si-title">${highlight(item.title, query)}</span>
          ${meta ? `<span class="tsj-si-meta">${meta}</span>` : ''}
        </span>
        <span class="tsj-si-arr"><i class="fa-solid fa-arrow-right"></i></span>
      </a>`;
  }

  /* ── RENDER RESULT CARD ─────────────────────────────────── */
  function renderResultCard(item, query) {
    const slug = item.slug || '#';
    const relTime = relativeTime(item.lastUpdated);
    const sectionLabel = item.sectionSource || item.cat || getSectionName(item.slug);
    // Dept: show org/dept but not if it's the same as sectionSource
    const deptLabel = item.dept && item.dept !== sectionLabel ? item.dept : '';
    
    // ✅ NEW: Show "NEW" badge if updated within last 7 days
    let isNew = false;
    if (item.lastUpdated) {
      const diffDays = (Date.now() - new Date(item.lastUpdated).getTime()) / 86400000;
      isNew = diffDays <= 7;
    }
    
    return `
      <div class="tsj-result-card">
        <div class="tsj-rc-head">
          <span class="tsj-rc-icon" aria-hidden="true"><i class="fa-solid ${esc(item.icon || 'fa-briefcase')}"></i></span>
          <div class="tsj-rc-info">
            <a class="tsj-rc-title" href="${esc(slug)}">${isNew ? '<span class="tsj-new-badge">NEW</span> ' : ''}${highlight(item.title, query)}</a>
            ${deptLabel ? `<div class="tsj-rc-dept">${esc(deptLabel)}</div>` : ''}
          </div>
        </div>
        <div class="tsj-rc-tags">
          ${item.qual ? `<span class="tsj-tag tsj-tag-qual"><i class="fa-solid fa-graduation-cap"></i> ${esc(item.qual)}</span>` : ''}
          ${item.state ? `<span class="tsj-tag tsj-tag-state"><i class="fa-solid fa-location-dot"></i> ${esc(item.state)}</span>` : ''}
          ${item.cat ? `<span class="tsj-tag tsj-tag-cat">${esc(item.cat)}</span>` : ''}
          ${item.lastDate ? `<span class="tsj-tag tsj-tag-date"><i class="fa-solid fa-clock"></i> ${esc(item.lastDate)}</span>` : ''}
        </div>
        <div class="tsj-rc-meta-row">
          <span class="tsj-section-badge"><i class="fa-solid fa-layer-group"></i> ${esc(sectionLabel)}</span>
          ${relTime ? `<span class="tsj-updated-time"><i class="fa-regular fa-clock"></i> ${esc(relTime)} अपडेट</span>` : ''}
        </div>
        <a class="tsj-rc-apply" href="${esc(slug)}"><i class="fa-solid fa-arrow-right"></i> View / Apply</a>
      </div>`;
  }

  /* ── TRENDING TAGS HTML ─────────────────────────────────── */
  function buildTrendingHtml() {
    return `
      <div class="tsj-trending" id="tsjTrending">
        <span class="tsj-tr-label"><i class="fa-solid fa-fire"></i> Trending:</span>
        <div class="tsj-tr-tags">
          ${TRENDING.map(t => `
            <button class="tsj-tr-tag" type="button" data-q="${esc(t.q)}">
              <i class="fa-solid ${esc(t.icon)}"></i> ${esc(t.label)}
            </button>`).join('')}
        </div>
      </div>`;
  }

  /* ── RECENT SEARCHES HTML ───────────────────────────────── */
  function buildRecentHtml() {
    const recent = getRecent();
    if (!recent.length) return '';
    return `
      <div class="tsj-recent">
        <div class="tsj-recent-hd">
          <span><i class="fa-solid fa-clock-rotate-left"></i> Recent Searches</span>
          <button type="button" id="tsjClearRecent" class="tsj-clear-btn">Clear</button>
        </div>
        <div class="tsj-recent-tags">
          ${recent.map(r => `<button class="tsj-recent-tag" type="button" data-q="${esc(r)}">${esc(r)}</button>`).join('')}
        </div>
      </div>`;
  }

  /* ── FILTERS HTML ───────────────────────────────────────── */
  function buildFiltersHtml() {
    const quals  = ['8th Pass', '10th Pass', '12th Pass', 'ITI', 'Diploma', 'Graduation', 'Post Graduation', 'B.Tech'];
    const states = ['All India', 'Haryana', 'Uttar Pradesh', 'Bihar', 'Rajasthan', 'Madhya Pradesh', 'Maharashtra', 'Punjab', 'Delhi'];
    const cats   = ['SSC', 'Railway', 'Bank', 'Police', 'Defence', 'Teaching', 'State Jobs', 'UPSC', 'Medical', 'ITI Jobs', 'PSU'];

    return `
      <div class="tsj-filters" id="tsjFilters">
        <div class="tsj-filter-row">
          <select class="tsj-filter-sel" id="fQual" aria-label="Filter by Qualification">
            <option value="">📚 All Qualifications</option>
            ${quals.map(q => `<option value="${esc(q)}">${esc(q)}</option>`).join('')}
          </select>
          <select class="tsj-filter-sel" id="fState" aria-label="Filter by State">
            <option value="">📍 All States</option>
            ${states.map(s => `<option value="${esc(s)}">${esc(s)}</option>`).join('')}
          </select>
          <select class="tsj-filter-sel" id="fCat" aria-label="Filter by Category">
            <option value="">🏷️ All Categories</option>
            ${cats.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('')}
          </select>
          <button type="button" class="tsj-filter-clear" id="tsjFilterClear">Reset</button>
        </div>
      </div>`;
  }

  /* ── INJECT CSS ─────────────────────────────────────────── */
  function injectStyles() {
    if (document.getElementById('tsj-search-styles')) return;
    const style = document.createElement('style');
    style.id = 'tsj-search-styles';
    style.textContent = `
      /* ── Search Wrapper ── */
      .tsj-search-wrap { position: relative; }

      /* ── Dropdown ── */
      #tsjDrop {
        background: #fff; border: 1px solid #e2e8f0;
        border-radius: 14px; box-shadow: 0 16px 48px rgba(13,34,87,.18);
        z-index: 99999; max-height: 420px; overflow-y: auto;
        display: none; animation: tsjFadeIn .15s ease;
      }
      #tsjDrop.open { display: block; }
      @keyframes tsjFadeIn { from { opacity:0; transform: translateY(-6px); } to { opacity:1; transform: translateY(0); } }

      /* ── Suggest items ── */
      .tsj-suggest-item {
        display: flex; align-items: center; gap: 10px;
        padding: 11px 14px; text-decoration: none; color: #0f172a;
        border-bottom: 1px solid #f8fafc; transition: background .1s; cursor: pointer;
      }
      .tsj-suggest-item:last-child { border-bottom: none; }
      .tsj-suggest-item:hover, .tsj-suggest-item.tsj-active { background: #eff6ff; }
      .tsj-si-icon { width: 30px; height: 30px; border-radius: 8px; background: #eff6ff; color: #1a56db; display: flex; align-items: center; justify-content: center; font-size: .8rem; flex-shrink: 0; }
      .tsj-si-body { flex: 1; overflow: hidden; }
      .tsj-si-title { display: block; font-size: .84rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .tsj-si-meta { display: block; font-size: .7rem; color: #64748b; margin-top: 1px; }
      .tsj-si-arr { color: #cbd5e1; font-size: .75rem; }
      .tsj-suggest-item:hover .tsj-si-arr, .tsj-suggest-item.tsj-active .tsj-si-arr { color: #1a56db; }

      /* ── Highlight ── */
      mark.srch-hl { background: #fef08a; color: #92400e; border-radius: 2px; padding: 0 1px; font-style: normal; }

      /* ── Trending ── */
      .tsj-trending { padding: 10px 14px 6px; border-bottom: 1px solid #f1f5f9; }
      .tsj-tr-label { font-size: .72rem; font-weight: 800; color: #f97316; display: block; margin-bottom: 7px; }
      .tsj-tr-tags { display: flex; flex-wrap: wrap; gap: 6px; }
      .tsj-tr-tag {
        background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa;
        border-radius: 20px; padding: 4px 10px; font-size: .7rem; font-weight: 700;
        cursor: pointer; transition: all .12s; font-family: inherit;
        display: flex; align-items: center; gap: 4px;
      }
      .tsj-tr-tag:hover { background: #f97316; color: #fff; border-color: #f97316; }

      /* ── Recent ── */
      .tsj-recent { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; }
      .tsj-recent-hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: 7px; font-size: .72rem; font-weight: 800; color: #475569; }
      .tsj-clear-btn { background: none; border: 1px solid #e2e8f0; border-radius: 6px; padding: 2px 8px; font-size: .68rem; color: #94a3b8; cursor: pointer; font-family: inherit; }
      .tsj-clear-btn:hover { color: #ef4444; border-color: #ef4444; }
      .tsj-recent-tags { display: flex; flex-wrap: wrap; gap: 5px; }
      .tsj-recent-tag {
        background: #f8fafc; color: #475569; border: 1px solid #e2e8f0;
        border-radius: 6px; padding: 4px 10px; font-size: .72rem; font-weight: 600;
        cursor: pointer; font-family: inherit; transition: all .12s;
      }
      .tsj-recent-tag:hover { background: #eff6ff; color: #1a56db; border-color: #bfdbfe; }

      /* ── Suggest more link ── */
      .tsj-suggest-more {
        display: flex; align-items: center; justify-content: center; gap: 6px;
        padding: 10px 14px; font-size: .78rem; font-weight: 700; color: #1a56db;
        text-decoration: none; border-top: 1px solid #f1f5f9; transition: background .12s;
      }
      .tsj-suggest-more:hover { background: #f0f9ff; }

      /* ── Suggest no results ── */
      .tsj-no-suggest { padding: 14px; font-size: .82rem; color: #94a3b8; text-align: center; }

      /* ── Full results panel ── */
      #tsjResultsPanel { margin-top: 12px; display: none; }
      #tsjResultsPanel.open { display: block; }

      /* ── Filters ── */
      .tsj-filters { margin-bottom: 10px; }
      .tsj-filter-row { display: flex; flex-wrap: wrap; gap: 6px; }
      .tsj-filter-sel {
        flex: 1; min-width: 130px; padding: 7px 10px; border: 1.5px solid #e2e8f0;
        border-radius: 8px; font-size: .78rem; font-weight: 600; color: #334155;
        background: #fff; font-family: inherit; cursor: pointer; outline: none;
        transition: border-color .15s;
      }
      .tsj-filter-sel:focus { border-color: #1a56db; }
      .tsj-filter-clear {
        padding: 7px 12px; background: #f1f5f9; border: 1.5px solid #e2e8f0;
        border-radius: 8px; font-size: .75rem; font-weight: 700; color: #64748b;
        cursor: pointer; font-family: inherit; transition: all .12s;
      }
      .tsj-filter-clear:hover { background: #ef4444; color: #fff; border-color: #ef4444; }

      /* ── Result cards ── */
      .tsj-results-grid { display: flex; flex-direction: column; gap: 8px; }
      .tsj-result-card {
        background: rgba(255,255,255,.92); border: 1px solid rgba(255,255,255,.5);
        border-radius: 10px; padding: 12px 14px; transition: all .15s;
        backdrop-filter: blur(4px);
      }
      .tsj-result-card:hover { background: #fff; box-shadow: 0 4px 16px rgba(13,34,87,.12); transform: translateY(-1px); }
      .tsj-rc-head { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 8px; }
      .tsj-rc-icon { width: 36px; height: 36px; border-radius: 10px; background: #eff6ff; color: #1a56db; display: flex; align-items: center; justify-content: center; font-size: .95rem; flex-shrink: 0; }
      .tsj-rc-info { flex: 1; }
      .tsj-rc-title { font-size: .86rem; font-weight: 800; color: #1a56db; text-decoration: none; display: block; line-height: 1.3; }
      .tsj-rc-title:hover { text-decoration: underline; }
      .tsj-rc-dept { font-size: .72rem; color: #64748b; margin-top: 2px; }
      .tsj-rc-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }
      .tsj-tag { font-size: .68rem; font-weight: 700; padding: 2px 8px; border-radius: 20px; display: flex; align-items: center; gap: 3px; }
      .tsj-tag-qual { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
      .tsj-tag-state { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
      .tsj-tag-cat { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
      .tsj-tag-date { background: #fff1f2; color: #be123c; border: 1px solid #fecdd3; }
      .tsj-rc-apply {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 5px 12px; background: #1a56db; color: #fff; border-radius: 6px;
        font-size: .72rem; font-weight: 800; text-decoration: none; transition: background .12s;
      }
      .tsj-rc-apply:hover { background: #1e40af; }

      /* ── Section Source Badge + Updated Time ── */
      .tsj-rc-meta-row {
        display: flex; align-items: center; gap: 8px;
        flex-wrap: wrap; margin-bottom: 8px;
      }
      .tsj-section-badge {
        display: inline-flex; align-items: center; gap: 4px;
        font-size: .66rem; font-weight: 700; padding: 2px 8px;
        border-radius: 20px;
        background: #f0f9ff; color: #0369a1;
        border: 1px solid #bae6fd;
      }
      .tsj-updated-time {
        display: inline-flex; align-items: center; gap: 4px;
        font-size: .66rem; font-weight: 600;
        color: #6b7280;
      }

      /* ── Results header ── */
      .tsj-res-head {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 10px; flex-wrap: wrap; gap: 6px;
      }
      .tsj-res-count { font-size: .8rem; color: rgba(255,255,255,.85); font-weight: 700; }
      .tsj-res-close {
        background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.3);
        border-radius: 7px; padding: 4px 10px; font-size: .72rem; font-weight: 700;
        color: #fff; cursor: pointer; font-family: inherit;
      }
      .tsj-res-close:hover { background: rgba(255,255,255,.25); }

      /* ── View all results link ── */
      .tsj-view-all-results {
        display: flex; align-items: center; justify-content: center; gap: 6px;
        margin-top: 10px; padding: 10px; background: rgba(255,255,255,.15);
        border: 1.5px solid rgba(255,255,255,.25); border-radius: 9px;
        color: #fff; font-size: .8rem; font-weight: 800; text-decoration: none;
        transition: background .15s;
      }
      .tsj-view-all-results:hover { background: rgba(255,255,255,.25); }



      /* ── NEW badge ── */
      .tsj-new-badge {
        display: inline-flex; align-items: center;
        background: #16a34a; color: #fff;
        font-size: .58rem; font-weight: 900; padding: 1px 5px;
        border-radius: 4px; margin-right: 3px; vertical-align: middle;
        letter-spacing: .05em;
      }

      @media (max-width: 480px) {
        #tsjDrop { border-radius: 10px; max-height: 400px; }
        .tsj-filter-sel { min-width: 100%; }
        .tsj-result-card { padding: 10px 11px; }
      }
    `;
    document.head.appendChild(style);
  }

  /* ── HERO SEARCH SETUP (Simple & Optimized v3.0) ──────── */
  function setupHeroSearch() {
    const input = document.getElementById('heroSearch');
    const btn   = document.getElementById('heroSearchBtn');
    if (!input) return;

    injectStyles();

    // Remove old suggest div (from index.html) if present
    const oldSuggest = document.getElementById('searchSuggest');
    if (oldSuggest) oldSuggest.remove();
    // Remove old results panel
    const oldPanel = document.getElementById('heroSearchResults');
    if (oldPanel) oldPanel.remove();

    // ── Create dropdown (fixed position, body-level so never clipped) ──
    const drop = document.createElement('div');
    drop.id = 'tsjDrop';
    drop.setAttribute('role', 'listbox');
    drop.setAttribute('aria-label', 'Job search suggestions');
    document.body.appendChild(drop);

    function positionDrop() {
      const rect = (input.closest('.hero-search-box') || input).getBoundingClientRect();
      drop.style.position  = 'fixed';
      drop.style.top       = (rect.bottom + 5) + 'px';
      drop.style.left      = rect.left + 'px';
      drop.style.width     = rect.width + 'px';
      drop.style.maxHeight = '400px';
      drop.style.zIndex    = '99999';
    }
    positionDrop();
    window.addEventListener('resize', () => { if (drop.classList.contains('open')) positionDrop(); });
    window.addEventListener('scroll', () => { if (drop.classList.contains('open')) positionDrop(); }, true);

    // ── Render one suggestion row ──
    // Shows: Job Title + direct job page URL as href
    function renderSuggestItem(item, q, idx) {
      const active = idx === activeIndex ? ' tsj-active' : '';
      const meta   = [item.sectionSource || item.cat, item.state && item.state !== 'All India' ? item.state : '']
                       .filter(Boolean).join(' · ');
      return `<a class="tsj-suggest-item${active}" href="${esc(item.slug)}" data-idx="${idx}" role="option">
        <span class="tsj-si-icon"><i class="fa-solid ${esc(item.icon || 'fa-briefcase')}"></i></span>
        <span class="tsj-si-body">
          <span class="tsj-si-title">${highlight(item.title, q)}</span>
          ${meta ? `<span class="tsj-si-meta">${esc(meta)}</span>` : ''}
        </span>
        <span class="tsj-si-arr"><i class="fa-solid fa-arrow-right"></i></span>
      </a>`;
    }

    // ── Open / close helpers ──
    function openDrop(html) {
      positionDrop();
      drop.innerHTML = html;
      drop.classList.add('open');
      // Wire recent tag clicks
      drop.querySelectorAll('.tsj-recent-tag').forEach(b => {
        b.addEventListener('click', () => { input.value = b.dataset.q; runSuggest(b.dataset.q); });
      });
      const clearBtn = drop.querySelector('#tsjClearRecent');
      if (clearBtn) {
        clearBtn.addEventListener('click', e => {
          e.stopPropagation();
          try { localStorage.removeItem(CFG.recentKey); } catch {}
          openDrop(`<div class="tsj-no-suggest">Type to search jobs…</div>`);
        });
      }
    }

    function closeDrop() {
      drop.classList.remove('open');
      drop.innerHTML = '';
      activeIndex   = -1;
      suggestItems  = [];
    }

    // ── Default dropdown (empty input) — show recent searches only ──
    function showDefaultDrop() {
      const recent = getRecent();
      const html = recent.length
        ? `<div class="tsj-recent">
             <div class="tsj-recent-hd">
               <span><i class="fa-solid fa-clock-rotate-left"></i> Recent Searches</span>
               <button type="button" id="tsjClearRecent" class="tsj-clear-btn">Clear</button>
             </div>
             <div class="tsj-recent-tags">
               ${recent.map(r => `<button class="tsj-recent-tag" type="button" data-q="${esc(r)}">${esc(r)}</button>`).join('')}
             </div>
           </div>`
        : `<div class="tsj-no-suggest">Type to search jobs, admit cards, results…</div>`;
      openDrop(html);
    }

    // ── Main suggest function — search & render results ──
    function runSuggest(q) {
      q = (q || '').trim();
      if (!q) { showDefaultDrop(); return; }

      const results = doSearch(q, {}).slice(0, CFG.maxSuggest);
      activeIndex  = -1;
      suggestItems = results;

      if (!results.length) {
        openDrop(`<div class="tsj-no-suggest">No results for "<strong>${esc(q)}</strong>". Try: SSC · Railway · Bank · Police · Army</div>`);
        return;
      }

      // Result rows: Job Title + direct job.html URL (href on the <a>)
      const rows = results.map((r, i) => renderSuggestItem(r, q, i)).join('');
      const footer = `<a class="tsj-suggest-more" href="${CFG.searchPageUrl}?q=${encodeURIComponent(q)}">
        <i class="fa-solid fa-magnifying-glass"></i> See all results for "${esc(q)}"
      </a>`;
      openDrop(rows + footer);

      // If JSON still loading — auto-refresh once it's ready
      if (!jsonIndexReady) {
        const savedQ = q;
        let tries = 0;
        (function wait() {
          if (input.value.trim().toLowerCase() !== savedQ.toLowerCase()) return;
          if (jsonIndexReady) { runSuggest(savedQ); }
          else if (tries++ < 20) { setTimeout(wait, 500); }
        })();
      }
    }

    // ── Keyboard navigation ──
    input.addEventListener('keydown', function (e) {
      const items = drop.querySelectorAll('.tsj-suggest-item');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIndex = Math.min(activeIndex + 1, items.length - 1);
        items.forEach((el, i) => el.classList.toggle('tsj-active', i === activeIndex));
        if (items[activeIndex]) items[activeIndex].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, -1);
        items.forEach((el, i) => el.classList.toggle('tsj-active', i === activeIndex));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const active = drop.querySelector('.tsj-suggest-item.tsj-active');
        if (active) {
          saveRecent(input.value.trim());
          window.location.href = active.href;  // direct job page open
        } else if (input.value.trim()) {
          saveRecent(input.value.trim());
          window.location.href = `${CFG.searchPageUrl}?q=${encodeURIComponent(input.value.trim())}`;
        }
        closeDrop();
      } else if (e.key === 'Escape') {
        closeDrop();
      }
    });

    // ── Input / focus events ──
    const debouncedSuggest = debounce(q => runSuggest(q), CFG.debounceMs);
    input.addEventListener('input', function () { debouncedSuggest(this.value); });
    input.addEventListener('focus', function () {
      if (this.value.trim().length >= 1) runSuggest(this.value);
      else showDefaultDrop();
    });

    // ── Search button — go to search page ──
    if (btn) {
      btn.addEventListener('click', () => {
        const q = input.value.trim();
        if (!q) return;
        saveRecent(q);
        closeDrop();
        window.location.href = `${CFG.searchPageUrl}?q=${encodeURIComponent(q)}`;
      });
    }

    // ── Click on suggestion → save recent, navigate to direct job URL ──
    drop.addEventListener('click', function (e) {
      const item = e.target.closest('.tsj-suggest-item');
      if (item) { saveRecent(input.value.trim()); closeDrop(); }
    });

    // ── Click outside → close ──
    document.addEventListener('click', function (e) {
      const box = input.closest('.hero-search-box') || input.parentElement;
      if (!drop.contains(e.target) && !box.contains(e.target)) closeDrop();
    });

    // ── Mobile search icon btn → scroll to hero & focus ──
    const mobileBtn = document.getElementById('mobileSearchBtn');
    if (mobileBtn) {
      mobileBtn.addEventListener('click', () => {
        const hero = document.getElementById('hero-search-section');
        if (hero) { hero.scrollIntoView({ behavior: 'smooth', block: 'start' }); setTimeout(() => input.focus(), 400); }
      });
    }
  }

  /* ── HEADER SEARCH SETUP ────────────────────────────────── */
  function setupHeaderSearch() {
    const hInput = document.getElementById('headerSearch');
    const hBtn   = document.getElementById('headerSearchBtn');
    if (hInput && hBtn) {
      hBtn.addEventListener('click', () => {
        if (hInput.value.trim()) window.location.href = `${CFG.searchPageUrl}?q=${encodeURIComponent(hInput.value.trim())}`;
      });
      hInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && hInput.value.trim()) window.location.href = `${CFG.searchPageUrl}?q=${encodeURIComponent(hInput.value.trim())}`;
      });
    }

    // openSearchBtn (mobile)
    const openBtn = document.getElementById('openSearchBtn');
    if (openBtn) {
      openBtn.addEventListener('click', () => {
        const heroInput = document.getElementById('heroSearch');
        if (heroInput) {
          const hero = document.getElementById('hero-search-section');
          if (hero) hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
          setTimeout(() => heroInput.focus(), 350);
        }
      });
    }
  }

  /* ── SEARCH.HTML PAGE HANDLER ───────────────────────────── */
  function setupSearchPage() {
    const container = document.getElementById('searchPageResults');
    if (!container) return;

    const params = new URLSearchParams(location.search);
    const q = params.get('q') || '';

    // Update page title + meta
    if (q) {
      document.title = `${q} – Jobs Search | Top Sarkari Jobs 2026`;
      const meta = document.querySelector('meta[name="description"]');
      if (meta) meta.content = `Search results for "${q}" – Find government jobs, results, admit cards on Top Sarkari Jobs.`;
    }

    // Sync input if present
    const pageInput = document.getElementById('searchPageInput');
    if (pageInput && q) pageInput.value = q;

    function renderPage(query) {
      const results = doSearch(query, currentFilters);
      container.innerHTML = results.length
        ? `<p class="sp-count">${results.length} result(s) for "<strong>${esc(query)}</strong>"</p>
           ${buildFiltersHtml()}
           <div class="tsj-results-grid sp-grid" id="tsjGrid">
             ${results.slice(0, 60).map(r => renderResultCard(r, query)).join('')}
           </div>`
        : `<p class="sp-count">No results found for "<strong>${esc(query)}</strong>". Try: SSC, Railway, Bank, Police, Haryana…</p>`;

      const fQual  = container.querySelector('#fQual');
      const fState = container.querySelector('#fState');
      const fCat   = container.querySelector('#fCat');
      const fReset = container.querySelector('#tsjFilterClear');
      const grid   = container.querySelector('#tsjGrid');

      function applyFilters() {
        currentFilters.qual  = fQual ? fQual.value : '';
        currentFilters.state = fState ? fState.value : '';
        currentFilters.cat   = fCat ? fCat.value : '';
        if (grid) grid.innerHTML = doSearch(query, currentFilters).slice(0, 60).map(r => renderResultCard(r, query)).join('');
      }
      if (fQual) fQual.addEventListener('change', applyFilters);
      if (fState) fState.addEventListener('change', applyFilters);
      if (fCat) fCat.addEventListener('change', applyFilters);
      if (fReset) fReset.addEventListener('click', () => {
        currentFilters = { qual: '', state: '', cat: '', sort: 'latest' };
        if (fQual) fQual.value = '';
        if (fState) fState.value = '';
        if (fCat) fCat.value = '';
        applyFilters();
      });

      if (pageInput) {
        pageInput.addEventListener('keydown', e => {
          if (e.key === 'Enter' && pageInput.value.trim()) {
            const newQ = pageInput.value.trim();
            history.replaceState(null, '', `${CFG.searchPageUrl}?q=${encodeURIComponent(newQ)}`);
            saveRecent(newQ);
            renderPage(newQ);
          }
        });
      }
    }

    if (q) {
      saveRecent(q);
      setTimeout(() => renderPage(q), 100); // wait for JSON load
    }

    container.insertAdjacentHTML('beforebegin', `
      <style>
        .sp-count { font-size:.88rem; color:#475569; font-weight:700; margin-bottom:12px; }
        .sp-grid { display:flex; flex-direction:column; gap:8px; }
        .tsj-result-card { background:#fff; border:1px solid #e2e8f0; }
        .tsj-result-card:hover { box-shadow:0 4px 16px rgba(13,34,87,.1); }
        .tsj-rc-title { color:#1a56db; }
        .tsj-res-count { color:#334155; }
      </style>`);
  }

  /* ── FIREWALL: block window.tsjSearchIndex completely ───────
   *  script.js pushes items from tools.json / jobs.json /
   *  services.json into window.tsjSearchIndex.
   *  We do NOT want any of that in search results.
   *  Data comes ONLY from the 4 approved JSON files loaded
   *  by loadJsonFiles() above.
   *  We neutralise tsjSearchIndex by replacing it with a
   *  dummy array that accepts writes but never feeds allData.
   * ─────────────────────────────────────────────────────────── */
  function installIndexFirewall() {
    // Replace any existing array with a silent dummy so script.js
    // can still call .push() without errors, but nothing leaks in.
    const dummy = Array.isArray(window.tsjSearchIndex)
      ? window.tsjSearchIndex.slice()   // keep reference length intact
      : [];

    window.tsjSearchIndex = new Proxy(dummy, {
      get(target, prop) { return target[prop]; },
      set(target, prop, value) {
        target[prop] = value;            // store silently — never touch allData
        return true;
      },
    });

    console.log('[smart-search] 🔒 tsjSearchIndex firewall active. ' +
                'Data source: 4 approved JSON files only.');
  }

  /* ── INIT ───────────────────────────────────────────────── */
  function init() {
    injectStyles();
    loadFuse(() => buildFuse(allData));
    loadJsonFiles(); // loads ONLY the 4 approved JSON files
    setupHeroSearch();
    setupHeaderSearch();
    setupSearchPage();

    // Block script.js from injecting tools/jobs/services into search
    installIndexFirewall();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
