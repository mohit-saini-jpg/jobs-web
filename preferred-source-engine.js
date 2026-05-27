/**
 * preferred-source-engine.js
 * Unified Smart "Set as Preferred Source on Google" Population System
 * Replaces populatePreferredSource + populatePreferredSourceNonJob
 * Works for: Job pages, Non-Job pages, Section pages, Fallback pages
 */
(function (root, factory) {
  root.TSJPreferredSource = factory();
}(this, function () {
  'use strict';

  /* ─────────────────────────────────────────────
     CATEGORY INTELLIGENCE DATABASE
     Maps every known slug / keyword to rich metadata
  ───────────────────────────────────────────── */
  var CAT_DB = {
    /* ── JOB CATEGORIES ── */
    'latest-notifications':     { label:'Latest Notifications', qual:'Any Qualification', postType:'Various Posts', selType:'Written Test / Interview', jobType:'Central Govt Job', salRange:'As per Govt norms', notifType:'Sarkari Recruitment' },
    '10th-pass':                { label:'10th Pass Jobs', qual:'Class 10th / Matric Pass', postType:'Group D / Constable', selType:'Written Test / Physical Test', jobType:'Govt Job', salRange:'₹18,000 – ₹35,000/month', notifType:'10th Pass Recruitment' },
    '12th-pass':                { label:'12th Pass Jobs', qual:'12th / Intermediate Pass', postType:'Clerk / Constable / LDC', selType:'Written Test / Document Verification', jobType:'Govt Job', salRange:'₹19,900 – ₹40,000/month', notifType:'12th Pass Recruitment' },
    'diploma':                  { label:'Diploma Jobs', qual:'Diploma (Engineering / Technical)', postType:'Junior Engineer / Technician', selType:'Written Test / Skill Test', jobType:'Technical Govt Job', salRange:'₹25,000 – ₹50,000/month', notifType:'Diploma Recruitment' },
    'iti':                      { label:'ITI Jobs', qual:'ITI / NCVT Certificate', postType:'Apprentice / Trade Apprentice', selType:'Merit / Written Test', jobType:'Skill-Based Govt Job', salRange:'₹14,000 – ₹30,000/month', notifType:'ITI Recruitment' },
    'btech':                    { label:'B.Tech / B.E. Jobs', qual:'B.Tech / B.E. Degree', postType:'Junior Engineer / Engineer', selType:'Written Test / Interview', jobType:'Technical Govt Job', salRange:'₹35,000 – ₹80,000/month', notifType:'Engineering Recruitment' },
    'bcom':                     { label:'B.Com Jobs', qual:'Bachelor of Commerce', postType:'Accountant / Auditor / Clerk', selType:'Written Test / Interview', jobType:'Finance Govt Job', salRange:'₹25,000 – ₹55,000/month', notifType:'Commerce Recruitment' },
    'graduation':               { label:'Any Graduate Jobs', qual:'Any Graduate (BA / B.Sc / B.Com)', postType:'Officer / Clerk / Assistant', selType:'Written Test / Interview', jobType:'Govt Job', salRange:'₹25,000 – ₹60,000/month', notifType:'Graduate Recruitment' },
    'post-graduation':          { label:'Post Graduate Jobs', qual:'Master\'s Degree (MA / M.Sc / MBA)', postType:'Officer / Specialist / Professor', selType:'Written Test / Interview', jobType:'Senior Govt Job', salRange:'₹40,000 – ₹1,00,000/month', notifType:'PG Recruitment' },
    'railway':                  { label:'Railway Jobs', qual:'10th Pass to Graduate', postType:'Group C / Group D / ALP / Technician', selType:'CBT Written Test / PET', jobType:'Central Govt / Railway Job', salRange:'₹18,000 – ₹70,000/month', notifType:'Railway Recruitment' },
    'police':                   { label:'Police / Defence Jobs', qual:'12th Pass / Graduation', postType:'Constable / SI / Inspector / Officer', selType:'Written Test / Physical / Medical Test', jobType:'Central / State Govt Job', salRange:'₹21,700 – ₹69,100/month', notifType:'Police Recruitment' },
    'army':                     { label:'Police / Defence Jobs', qual:'10th / 12th Pass', postType:'Soldier / Sepoy / Officer', selType:'Physical Test / Written Test / Medical', jobType:'Defence Govt Job', salRange:'₹21,700 – ₹56,900/month', notifType:'Army Recruitment' },
    'teaching':                 { label:'Teaching / Faculty Jobs', qual:'B.Ed / D.El.Ed / NET / STET', postType:'PGT / TGT / Assistant Professor', selType:'Written Test / Demo / Interview', jobType:'Education Govt Job', salRange:'₹35,400 – ₹1,12,400/month', notifType:'Teaching Recruitment' },
    'bank':                     { label:'Bank Jobs', qual:'Graduation (Any Stream)', postType:'PO / Clerk / SO / Officer', selType:'Online Written Test / Interview', jobType:'Bank / PSU Job', salRange:'₹30,000 – ₹85,000/month', notifType:'Banking Recruitment' },
    'medical':                  { label:'Medical / Hospital Jobs', qual:'MBBS / B.Pharma / GNM / BSc Nursing', postType:'Doctor / Nurse / Pharmacist / Staff Nurse', selType:'Written Test / Interview', jobType:'Medical Govt Job', salRange:'₹25,000 – ₹1,20,000/month', notifType:'Medical Recruitment' },
    'upcoming':                 { label:'Upcoming Jobs', qual:'Various Qualifications', postType:'Various Posts', selType:'To be Announced', jobType:'Govt Job', salRange:'As per notification', notifType:'Upcoming Recruitment' },
    'state':                    { label:'State Govt Jobs', qual:'10th Pass to Graduation', postType:'Various State Govt Posts', selType:'Written Test / Document Verification', jobType:'State Govt Job', salRange:'As per State Pay Scale', notifType:'State Recruitment' },
    'central':                  { label:'Central Govt Jobs', qual:'10th Pass to Post Graduate', postType:'Central Govt Posts', selType:'Written Test / Interview', jobType:'Central Govt Job', salRange:'As per 7th Pay Commission', notifType:'Central Recruitment' },
    'offline':                  { label:'Offline Form Jobs', qual:'10th Pass to Graduation', postType:'Various Govt Posts', selType:'Written Test / Interview', jobType:'Govt Job', salRange:'As per notification', notifType:'Offline Application' },
    /* ── NON-JOB CATEGORIES ── */
    'result':                   { label:'Sarkari Result', qual:'—', postType:'Exam Result', selType:'Merit Based', jobType:'Govt Exam Result', salRange:'—', notifType:'Result Declaration', updateType:'Result Update', schemeType:'—' },
    'admit-card':               { label:'Admit Card', qual:'—', postType:'Hall Ticket / Call Letter', selType:'Exam Entry Slip', jobType:'Govt Exam Card', salRange:'—', notifType:'Admit Card Release', updateType:'Admit Card', schemeType:'—' },
    'admission':                { label:'Admission', qual:'Various Academic Qualifications', postType:'Admission Seat', selType:'Entrance Exam / Merit', jobType:'Admission / Enrollment', salRange:'—', notifType:'Admission Notification', updateType:'Admission Update', schemeType:'—' },
    'answer-key':               { label:'Answer Key', qual:'—', postType:'Answer Key PDF', selType:'Official Answer Key', jobType:'Exam Answer Key', salRange:'—', notifType:'Answer Key Release', updateType:'Answer Key', schemeType:'—' },
    'offline-form':             { label:'Offline Form', qual:'Various', postType:'Offline Application Form', selType:'Document Submission', jobType:'Govt Job', salRange:'As per notification', notifType:'Offline Form', updateType:'Form Update', schemeType:'—' },
    'scheme':                   { label:'Govt Scheme / Yojna', qual:'Indian Citizen', postType:'Beneficiary Enrollment', selType:'Eligibility Based', jobType:'Govt Benefit', salRange:'Varies by Scheme', notifType:'Scheme Notification', updateType:'Scheme Update', schemeType:'Central / State Govt Scheme' },
    'csc':                      { label:'CSC Resource', qual:'VLE / CSC Operator', postType:'CSC Service', selType:'Direct Access', jobType:'Digital India Service', salRange:'Commission Based', notifType:'CSC Update', updateType:'CSC PDF / Link', schemeType:'Digital Seva' },
    'today-updates':            { label:'Today Updates', qual:'All Citizens', postType:'Daily Update', selType:'Information', jobType:'Sarkari Update', salRange:'—', notifType:'Daily Update', updateType:'Today\'s Latest Update', schemeType:'—' },
  };

  /* ── Qualification lookup from title keywords ── */
  var QUAL_KEYWORDS = [
    [/10th|matric|ssc\b|class\s*10/i,                 '10th / Matric Pass'],
    [/12th|inter(?:mediate)?|hsc|plus\s*2/i,          '12th / Intermediate Pass'],
    [/iti\b|ncvt|scvt/i,                               'ITI / Trade Certificate'],
    [/diploma/i,                                        'Diploma (Engineering/Technical)'],
    [/b\.?tech|b\.?e\b|engineering\s+degree/i,         'B.Tech / B.E.'],
    [/b\.?sc|bachelor\s+of\s+science/i,                'B.Sc Degree'],
    [/b\.?com|bachelor\s+of\s+commerce/i,              'B.Com Degree'],
    [/b\.?a\b|bachelor\s+of\s+arts/i,                  'BA Degree'],
    [/m\.?b\.?b\.?s|medical\s+degree/i,               'MBBS / Medical Degree'],
    [/b\.?pharma|pharmacy/i,                            'B.Pharma / Pharmacy'],
    [/gnm|anm|nursing/i,                                'GNM / ANM / Nursing'],
    [/llb|law\s+degree/i,                               'LLB / Law Degree'],
    [/mba|master\s+of\s+business/i,                    'MBA / Master\'s Degree'],
    [/m\.?sc|master\s+of\s+science/i,                  'M.Sc Degree'],
    [/ma\b|master\s+of\s+arts/i,                       'MA / Master\'s Degree'],
    [/ph\.?d|doctorate/i,                               'Ph.D / Doctorate'],
    [/post\s*grad|pg\b/i,                               'Post Graduate'],
    [/b\.?ed|bed\b/i,                                   'B.Ed (Bachelor of Education)'],
    [/graduate|graduation|any\s+degree/i,               'Any Graduate (Any Stream)'],
  ];

  /* ── Organisation extraction from title ── */
  var ORG_PATTERNS = [
    [/\b(upsc)\b/i,                                     'UPSC (Union Public Service Commission)'],
    [/\b(ssc)\b/i,                                      'SSC (Staff Selection Commission)'],
    [/\b(rrb|railway\s*recruitment\s*board)\b/i,        'Railway Recruitment Board (RRB)'],
    [/\b(rrb-?ntpc|ntpc)\b/i,                           'RRB-NTPC (Indian Railways)'],
    [/\b(ibps)\b/i,                                     'IBPS (Institute of Banking Personnel Selection)'],
    [/\b(sbi)\b/i,                                      'SBI (State Bank of India)'],
    [/\b(rbi)\b/i,                                      'RBI (Reserve Bank of India)'],
    [/\b(niacl|nicl|lic\b)/i,                           'LIC / NIACL / NICL (Insurance)'],
    [/\b(crpf)\b/i,                                     'CRPF (Central Reserve Police Force)'],
    [/\b(bsf)\b/i,                                      'BSF (Border Security Force)'],
    [/\b(cisf)\b/i,                                     'CISF (Central Industrial Security Force)'],
    [/\b(itbp)\b/i,                                     'ITBP (Indo-Tibetan Border Police)'],
    [/\b(ssb)\b/i,                                      'SSB (Sashastra Seema Bal)'],
    [/\b(nda|cds|afcat)\b/i,                            'Indian Armed Forces (NDA/CDS/AFCAT)'],
    [/\b(aiims)\b/i,                                    'AIIMS (All India Institute of Medical Sciences)'],
    [/\b(esic)\b/i,                                     'ESIC (Employees State Insurance Corporation)'],
    [/\b(epfo)\b/i,                                     'EPFO (Employees Provident Fund Organisation)'],
    [/\b(npcil)\b/i,                                    'NPCIL (Nuclear Power Corporation of India)'],
    [/\b(drdo)\b/i,                                     'DRDO (Defence Research and Development Organisation)'],
    [/\b(isro)\b/i,                                     'ISRO (Indian Space Research Organisation)'],
    [/\b(hal)\b/i,                                      'HAL (Hindustan Aeronautics Limited)'],
    [/\b(ongc)\b/i,                                     'ONGC (Oil and Natural Gas Corporation)'],
    [/\b(bhel)\b/i,                                     'BHEL (Bharat Heavy Electricals Limited)'],
    [/\b(ntpc)\b/i,                                     'NTPC (National Thermal Power Corporation)'],
    [/\b(bel)\b/i,                                      'BEL (Bharat Electronics Limited)'],
    [/\b(nhpc)\b/i,                                     'NHPC (National Hydroelectric Power Corporation)'],
    [/\b(sail)\b/i,                                     'SAIL (Steel Authority of India Ltd)'],
    [/\b(pnb)\b/i,                                      'PNB (Punjab National Bank)'],
    [/\b(boi)\b/i,                                      'BOI (Bank of India)'],
    [/\b(bob)\b/i,                                      'BOB (Bank of Baroda)'],
    [/\b(kvs)\b/i,                                      'KVS (Kendriya Vidyalaya Sangathan)'],
    [/\b(nvs)\b/i,                                      'NVS (Navodaya Vidyalaya Samiti)'],
    [/\b(dfccil)\b/i,                                   'DFCCIL (Dedicated Freight Corridor Corporation)'],
    [/\b(nmrc|metro)\b/i,                               'Metro Rail Corporation'],
    [/\bhigh\s*court/i,                                  'High Court'],
    [/\b(har[a-z]?yana|hpsc|hssc|hbse)\b/i,            'Haryana Govt / HSSC / HPSC'],
    [/\b(rajasthan|rpsc|rsmssb)\b/i,                    'Rajasthan Govt / RPSC / RSMSSB'],
    [/\b(uttar\s*pradesh|up\b|uppsc|upsssc)\b/i,        'UP Govt / UPPSC / UPSSSC'],
    [/\b(madhya\s*pradesh|mp\b|mppsc|mpesb)\b/i,        'MP Govt / MPPSC / MPESB'],
    [/\b(bihar|bpsc|bssc)\b/i,                          'Bihar Govt / BPSC / BSSC'],
    [/\b(jharkhand|jpsc|jssc)\b/i,                      'Jharkhand Govt / JPSC / JSSC'],
    [/\b(odisha|opsc|ossc)\b/i,                         'Odisha Govt / OPSC / OSSC'],
    [/\b(gujarat|gpsc|gsssb)\b/i,                       'Gujarat Govt / GPSC / GSSSB'],
    [/\b(maharashtra|mpsc|maha)\b/i,                    'Maharashtra Govt / MPSC'],
    [/\b(karnataka|kpsc|ksrp)\b/i,                      'Karnataka Govt / KPSC'],
    [/\b(tamil\s*nadu|tnpsc)\b/i,                       'Tamil Nadu Govt / TNPSC'],
    [/\b(andhra|appsc)\b/i,                             'Andhra Pradesh Govt / APPSC'],
    [/\b(telangana|tspsc)\b/i,                          'Telangana Govt / TSPSC'],
    [/\b(punjab|ppsc|psssb)\b/i,                        'Punjab Govt / PPSC'],
    [/\b(himachal|hppsc|hp\b)\b/i,                      'Himachal Pradesh Govt / HPPSC'],
    [/\b(uttarakhand|ukpsc|uksssc)\b/i,                 'Uttarakhand Govt / UKPSC'],
    [/\b(assam|apsc|slprb)\b/i,                         'Assam Govt / APSC'],
    [/\b(west\s*bengal|wbpsc|wbssc)\b/i,                'West Bengal Govt / WBPSC'],
    [/\b(delhi|dsssb|dnhdd)\b/i,                        'Delhi Govt / DSSSB'],
    [/\b(kerala|kpsc|psc\b)\b/i,                        'Kerala Govt / KPSC'],
    [/\b(goa|gpsc\b)\b/i,                               'Goa Govt / GPSC'],
  ];

  /* ── Location extraction from title / slug ── */
  var LOC_PATTERNS = [
    [/haryana/i,          'Haryana'],    [/rajasthan/i,        'Rajasthan'],
    [/uttar\s*pradesh|\bup\s+(?:police|pcs|si|bpsc|govt|board|ssc)\b|\buppsc\b|\bupsssc\b/i, 'Uttar Pradesh'],
    [/madhya\s*pradesh/i, 'Madhya Pradesh'],
    [/bihar/i,            'Bihar'],      [/jharkhand/i,        'Jharkhand'],
    [/odisha/i,           'Odisha'],     [/gujarat/i,          'Gujarat'],
    [/maharashtra/i,      'Maharashtra'],[/karnataka/i,        'Karnataka'],
    [/tamil\s*nadu/i,     'Tamil Nadu'], [/andhra/i,           'Andhra Pradesh'],
    [/telangana/i,        'Telangana'],  [/punjab/i,           'Punjab'],
    [/himachal/i,         'Himachal Pradesh'],
    [/uttarakhand/i,      'Uttarakhand'],
    [/assam/i,            'Assam'],      [/west\s*bengal/i,    'West Bengal'],
    [/delhi/i,            'Delhi'],      [/kerala/i,           'Kerala'],
    [/goa/i,              'Goa'],        [/tripura/i,          'Tripura'],
    [/manipur/i,          'Manipur'],    [/meghalaya/i,        'Meghalaya'],
    [/nagaland/i,         'Nagaland'],   [/mizoram/i,          'Mizoram'],
    [/arunachal/i,        'Arunachal Pradesh'],
    [/sikkim/i,           'Sikkim'],     [/chhattisgarh/i,    'Chhattisgarh'],
    [/jammu|kashmir/i,    'Jammu & Kashmir'],
  ];

  var _s = function (v) { return (v == null ? '' : String(v)).trim(); };

  /* ─────────────────────────────────────────────
     detectCategoryFromContext
     Returns a rich category meta object
  ───────────────────────────────────────────── */
  function detectCategoryFromContext(opts) {
    var title   = _s(opts.title   || '').toLowerCase();
    var slug    = _s(opts.slug    || '').toLowerCase();
    var section = _s(opts.section || '').toLowerCase();
    var combined = title + ' ' + slug + ' ' + section;

    /* Priority order: more specific first */
    /* NON-JOB types */
    if (/result|merit\s*list|cut.?off|score.?card/i.test(combined) && !/recruitment/i.test(combined))
      return CAT_DB['result'];
    if (/admit\s*card|hall\s*ticket|call\s*letter/i.test(combined))
      return CAT_DB['admit-card'];
    if (/answer\s*key/i.test(combined))
      return CAT_DB['answer-key'];
    if (/admission|admissions/i.test(combined))
      return CAT_DB['admission'];
    if (/scheme|yojna|yojana/i.test(combined))
      return CAT_DB['scheme'];
    if (/csc|digital\s*seva|vle/i.test(combined))
      return CAT_DB['csc'];
    if (/today.*update|daily.*update/i.test(combined))
      return CAT_DB['today-updates'];
    if (/offline.*form/i.test(combined))
      return CAT_DB['offline-form'];

    /* JOB types */
    if (/\bupsc\b|\bssc\b|\bsssc\b/i.test(combined))
      return CAT_DB['central'];
    if (/railway|rrb|metro\s*rail|dfccil/i.test(combined))
      return CAT_DB['railway'];
    if (/bank|sbi\b|rbi\b|ibps|pnb|boi\b|bob\b|lic\b|niacl|nicl/i.test(combined))
      return CAT_DB['bank'];
    if (/police|constable|\bcisf\b|\bcrpf\b|\bbsf\b|\bitbp\b|\bssb\b/i.test(combined))
      return CAT_DB['police'];
    if (/army|navy|air\s*force|defence|nda\b|cds\b|afcat/i.test(combined))
      return CAT_DB['army'];
    if (/teach|faculty|tgt\b|pgt\b|kvs\b|nvs\b|b\.ed|bed\b|professor/i.test(combined))
      return CAT_DB['teaching'];
    if (/medical|hospital|aiims|nurse|nursing|pharmacist|mbbs|doctor/i.test(combined))
      return CAT_DB['medical'];
    if (/b\.?tech|b\.?e\b|btech|engineer|psu\b|npcil|drdo|isro|hal\b|bhel|ntpc|bel\b/i.test(combined))
      return CAT_DB['btech'];
    if (/b\.?com|bcom|account|audit|finance/i.test(combined))
      return CAT_DB['bcom'];
    if (/iti\b|ncvt|apprentice/i.test(combined))
      return CAT_DB['iti'];
    if (/diploma/i.test(combined))
      return CAT_DB['diploma'];
    if (/post\s*grad|pg\b|master|mba|msc|ma\b/i.test(combined))
      return CAT_DB['post-graduation'];
    if (/10th|matric|class\s*10/i.test(combined))
      return CAT_DB['10th-pass'];
    if (/12th|intermediate|hsc/i.test(combined))
      return CAT_DB['12th-pass'];
    if (/upcoming/i.test(combined))
      return CAT_DB['upcoming'];
    if (/state.*job|state.*govt/i.test(combined))
      return CAT_DB['state'];
    if (/central.*job|central.*govt/i.test(combined))
      return CAT_DB['central'];
    if (/graduat|any\s+graduate|any\s+degree/i.test(combined))
      return CAT_DB['graduation'];

    return CAT_DB['latest-notifications'];
  }

  /* ─────────────────────────────────────────────
     extractOrg: smart org extraction
  ───────────────────────────────────────────── */
  function extractOrg(title, rowOrg, slug) {
    var combined = _s(title) + ' ' + _s(slug);
    /* 1. Try org patterns */
    for (var i = 0; i < ORG_PATTERNS.length; i++) {
      if (ORG_PATTERNS[i][0].test(combined)) return ORG_PATTERNS[i][1];
    }
    /* 2. Use row.org if meaningful */
    if (rowOrg && rowOrg.length > 3 && rowOrg !== '—') return rowOrg;
    /* 3. Derive from title: extract first meaningful word cluster */
    var words = _s(title).replace(/\s+(2024|2025|2026|2027).*/i, '').split(/\s+/);
    var stopRx = /^(various|online|form|result|admit|answer|key|syllabus|post|posts|vacancy|vacancies|recruitment|notification|application|latest|upcoming|state|central|govt|government|sarkari|india|all|important|link|pdf|download|yojna|yojana|scheme|pm\b|pradhan)$/i;
    var org = [];
    for (var j = 0; j < Math.min(words.length, 7); j++) {
      if (stopRx.test(words[j])) break;
      org.push(words[j]);
    }
    /* If org is just PM / scheme / yojna style, return Govt of India */
    var orgStr = org.join(' ').replace(/[,.:]+$/, '');
    if (!orgStr || /^(pm|pradhan|mukhya|chief|atal|indira|rajiv)/i.test(orgStr)) return 'Government of India';
    return orgStr;
  }

  /* ─────────────────────────────────────────────
     extractLocation: smart location detection
  ───────────────────────────────────────────── */
  function extractLocation(title, rowLocation, slug) {
    if (rowLocation && rowLocation !== 'All India' && rowLocation !== '—') return rowLocation;
    var combined = _s(title) + ' ' + _s(slug);
    for (var i = 0; i < LOC_PATTERNS.length; i++) {
      if (LOC_PATTERNS[i][0].test(combined)) return LOC_PATTERNS[i][1];
    }
    return 'All India';
  }

  /* ─────────────────────────────────────────────
     extractQualification: smart qual detection
  ───────────────────────────────────────────── */
  function extractQualification(title, catMeta) {
    var t = _s(title);
    for (var i = 0; i < QUAL_KEYWORDS.length; i++) {
      if (QUAL_KEYWORDS[i][0].test(t)) return QUAL_KEYWORDS[i][1];
    }
    return catMeta ? catMeta.qual : 'Any Qualification';
  }

  /* ─────────────────────────────────────────────
     extractVacancies: smart vacancy extraction
  ───────────────────────────────────────────── */
  function extractVacancies(title, rowVac, parsed) {
    /* 1. From row data */
    if (rowVac && rowVac !== '—' && !/see/i.test(rowVac)) return rowVac;
    /* 2. From parsed */
    if (parsed && parsed.vac) return parsed.vac;
    /* 3. From title */
    var m = _s(title).match(/([\d,]+)\s*(?:posts?|vacancies|vacancy|seats?)/i);
    if (m) return m[1].replace(/,/g, '');
    /* Try number before common dept keywords */
    var m2 = _s(title).match(/\b([\d,]{3,})\s*(?:group|constable|officer|post|clerk|si\b)/i);
    if (m2) return m2[1].replace(/,/g, '');
    /* 4. Smart fallback based on keywords */
    if (/top\s*20/i.test(title)) return '20+ Posts';
    if (/100\+|hundreds/i.test(title)) return '100+ Posts';
    if (/1000\+|thousands/i.test(title)) return '1000+ Posts';
    return 'Multiple Posts';
  }

  /* ─────────────────────────────────────────────
     extractApplyMode: smart apply mode detection
  ───────────────────────────────────────────── */
  function extractApplyMode(title, slug, rowApplyMode) {
    if (rowApplyMode && rowApplyMode !== '—') return rowApplyMode;
    var combined = (_s(title) + ' ' + _s(slug)).toLowerCase();
    if (/offline|postal/i.test(combined)) return 'Offline';
    if (/walk.?in/i.test(combined)) return 'Walk-in';
    if (/download/i.test(combined)) return 'Download';
    return 'Online';
  }

  /* ─────────────────────────────────────────────
     extractLastDate: best last date guess
  ───────────────────────────────────────────── */
  function extractLastDate(title, rowLastDate, parsed) {
    if (rowLastDate && rowLastDate !== '—' && !/see/i.test(rowLastDate)) return rowLastDate;
    if (parsed && parsed.lastDt) return parsed.lastDt;
    var m = _s(title).match(/last\s*date[:\s–\-]+(\d{1,2}[-\/][A-Za-z0-9]{2,3}[-\/]\d{2,4}|\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})/i);
    if (m) return m[1].trim();
    return null;
  }

  /* ─────────────────────────────────────────────
     buildSmartDescription: 160-char rich description
  ───────────────────────────────────────────── */
  function buildSmartDescription(title, catMeta, org, vac, lastDate, isJob) {
    var t = _s(title);
    if (isJob) {
      var parts = [t];
      if (org && org !== 'Government of India') parts.push(org);
      if (vac && vac !== 'Multiple Posts') parts.push(vac + ' Posts');
      if (catMeta && catMeta.qual) parts.push('Eligibility: ' + catMeta.qual);
      if (lastDate) parts.push('Last Date: ' + lastDate);
      parts.push('Apply at Top Sarkari Jobs.');
      var desc = parts.join(' | ');
      return desc.length > 200 ? desc.substring(0, 197) + '...' : desc;
    } else {
      /* Non-job */
      var type = (catMeta && catMeta.label) || 'Sarkari Update';
      return t + ' | ' + type + ' — Get latest updates, official links and direct download at Top Sarkari Jobs.';
    }
  }

  /* ─────────────────────────────────────────────
     setEl: safe setter
  ───────────────────────────────────────────── */
  function setEl(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = _s(value);
    return el;
  }
  function setHTML(id, html) {
    var el = document.getElementById(id);
    if (el) el.innerHTML = html;
    return el;
  }
  function showEl(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = '';
    return el;
  }

  /* ─────────────────────────────────────────────
     buildBadgeHTML: form-mode badge
  ───────────────────────────────────────────── */
  function buildBadgeHTML(mode, type) {
    var m = _s(mode).toLowerCase();
    var cls = m.includes('offline') ? 'offline' : m.includes('walk') ? 'walkin' : m.includes('download') ? 'download' : 'online';
    return '<span class="jp-ps-badge ' + cls + '">' + _s(mode) + ' ' + (type || 'Form') + '</span>';
  }

  /* ─────────────────────────────────────────────
     PUBLIC API: populateUnified
     The ONE function that replaces both old functions.
     opts = {
       isJob      : bool,
       title      : string,    (page title / job name)
       slug       : string,    (URL slug)
       section    : string,    (section name)
       row        : object,    (JSON row if available)
       parsed     : object,    (parseJob() result)
       cardId     : string,    (DOM id of the card)
       descId     : string,    (DOM id for description)
       formModeId : string,
       jobStateId : string,
       totalPostsId: string,
       jobTypeId  : string,
       orgId      : string,
     }
  ───────────────────────────────────────────── */
  function populateUnified(opts) {
    opts = opts || {};
    var cardId      = opts.cardId      || (opts.isJob ? 'preferredSourceCard' : 'preferredSourceCardNJ');
    var psCard      = document.getElementById(cardId);
    if (!psCard) return;

    var title   = _s(opts.title);
    var slug    = _s(opts.slug || window.__TSJ_SLUG || '');
    var section = _s(opts.section);
    var row     = opts.row || null;
    var parsed  = opts.parsed || null;
    var isJob   = opts.isJob !== false; /* default true */

    /* 1. Detect category */
    var catMeta = detectCategoryFromContext({ title: title, slug: slug, section: section });

    /* 2. Extract all fields smartly */
    var org      = extractOrg(title, row && (row.org || row.organisation), slug);
    var location = extractLocation(title, row && row.jobLocation, slug);
    var qual     = extractQualification(title, catMeta);
    var vac      = extractVacancies(title, row && (row.totalVac || row.vac), parsed);
    var applyMode= extractApplyMode(title, slug, row && row.applyMode);
    var lastDate = extractLastDate(title, row && (row.lastDate || row.last_date), parsed);
    var jobType  = (row && row.jobType) || (parsed && parsed.category && parsed.category.label) || catMeta.label || 'Govt Job';
    var isNonJob = !isJob;

    /* 3. Build description */
    var desc;
    if (row && row.shortInfo && row.shortInfo.length > 20) {
      desc = row.shortInfo.length > 200 ? row.shortInfo.substring(0, 197) + '...' : row.shortInfo;
    } else {
      desc = buildSmartDescription(title, catMeta, org, vac, lastDate, isJob);
    }

    /* 4. Determine ids (support both job and non-job card layouts) */
    var sfx = isNonJob ? 'NJ' : '';
    var descId       = opts.descId       || ('psDesc'       + sfx);
    var formModeId   = opts.formModeId   || ('psFormMode'   + sfx);
    var jobStateId   = opts.jobStateId   || ('psJobState'   + sfx);
    var totalPostsId = opts.totalPostsId || ('psTotalPosts' + sfx);
    var jobTypeId    = opts.jobTypeId    || ('psJobType'    + sfx);
    var orgId        = opts.orgId        || ('psOrgName'    + sfx);

    /* 5. Populate description */
    setEl(descId, desc);

    /* 6. Populate Form Mode badge */
    var modeLabel = isNonJob
      ? (applyMode === 'Download' ? 'Download' : applyMode === 'Offline' ? 'Offline' : 'Online')
      : applyMode;
    var modeType  = isNonJob ? 'Link' : 'Form';
    setHTML(formModeId, buildBadgeHTML(modeLabel, modeType));

    /* 7. Populate Job State / Location */
    setEl(jobStateId, location);

    /* 8. Populate Total Posts */
    var postsText = vac;
    if (isJob && postsText && !/posts?$/i.test(postsText) && !/^multiple/i.test(postsText) && !/see/i.test(postsText)) {
      postsText = postsText + ' Posts';
    }
    setEl(totalPostsId, postsText || (isNonJob ? catMeta.label : 'Multiple Posts'));

    /* 9. Populate Job Type */
    var jtShort = _s(jobType);
    if (jtShort.length > 20) jtShort = jtShort.substring(0, 18) + '..';
    setEl(jobTypeId, jtShort);

    /* 10. Populate Organisation */
    var orgEl = document.getElementById(orgId);
    if (orgEl) {
      var orgFull = isNonJob ? (org !== 'Government of India' ? org : 'Top Sarkari Jobs — India No.1 Portal') : org;
      orgEl.textContent = orgFull.length > 60 ? orgFull.substring(0, 58) + '..' : orgFull;
      orgEl.title = orgFull;
    }

    /* 11. Show the card */
    psCard.style.display = '';
  }

  /* ─────────────────────────────────────────────
     PUBLIC API: populateSectionCard
     For section/index pages that use svPreferredCard
  ───────────────────────────────────────────── */
  function populateSectionCard(opts) {
    opts = opts || {};
    var card = document.getElementById(opts.cardId || 'svPreferredCard');
    if (!card) return;

    var slug    = _s(opts.slug    || '');
    var section = _s(opts.section || slug);
    var title   = _s(opts.title   || section.replace(/-/g, ' ').replace(/\b./g, function(c){ return c.toUpperCase(); }));
    var count   = opts.count;  /* total item count, number */

    var catMeta = detectCategoryFromContext({ title: title, slug: slug, section: section });
    var location = extractLocation(title, null, slug);
    var applyMode= extractApplyMode(title, slug, null);

    /* Description */
    var countStr = (count && count > 0) ? count + ' listings' : 'Latest';
    var descText = title + ' 2026 | ' + countStr + ' — Get ' + catMeta.label + ' notifications, eligibility, vacancies, results and admit cards at Top Sarkari Jobs.';

    /* Page type badge */
    var pageType = catMeta.label;
    var mode = applyMode;

    var descEl = document.getElementById(opts.descId || 'svPsDesc');
    if (descEl) descEl.textContent = descText;

    var ptEl = document.getElementById(opts.pageTypeId || 'svPsPageType');
    if (ptEl) {
      var cls = /offline/i.test(mode) ? 'offline' : /walk/i.test(mode) ? 'walkin' : 'online';
      ptEl.textContent = pageType;
      ptEl.className = 'sv-ps-badge ' + cls;
    }

    var catEl = document.getElementById(opts.categoryId || 'svPsCategory');
    if (catEl) catEl.textContent = title;

    var modeEl = document.getElementById(opts.modeId || 'svPsMode');
    if (modeEl) modeEl.textContent = mode + ' Form';

    var locEl = document.getElementById(opts.locationId || 'svPsLocation');
    if (locEl) locEl.textContent = location;

    card.style.display = '';
  }

  /* ─────────────────────────────────────────────
     PUBLIC API: populateFallback
     Guarantees a card always renders, even with zero data
  ───────────────────────────────────────────── */
  function populateFallback(opts) {
    opts = opts || {};
    var slug  = _s(opts.slug || window.__TSJ_SLUG || window.location.pathname.split('/').filter(Boolean).pop() || '');
    var title = _s(opts.title || slug.replace(/-/g, ' ').replace(/\b./g, function(c){ return c.toUpperCase(); }) || 'Sarkari Jobs 2026');
    populateUnified({ isJob: opts.isJob, title: title, slug: slug, cardId: opts.cardId });
  }

  return {
    populate         : populateUnified,
    populateSection  : populateSectionCard,
    populateFallback : populateFallback,
    detectCategory   : detectCategoryFromContext,
    extractOrg       : extractOrg,
    extractLocation  : extractLocation,
    extractQualification : extractQualification,
    extractVacancies : extractVacancies,
  };
}));
