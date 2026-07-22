/* TSJ AI — floating government-job assistant widget.
   Self-contained: injects its own CSS + HTML, no page markup changes needed.
   Talks to /api/chat (Vercel Edge Function) only — never calls Groq/Tavily
   directly, so no API key is ever exposed to the browser. */
(function(){
'use strict';
if(window.__TSJ_CHAT_LOADED) return;
window.__TSJ_CHAT_LOADED = true;

/* ============================== CONFIG ============================== */
var SEARCH_INDEX_URL = '/chat-search-index.json';
var FUSE_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/fuse.js/7.0.0/fuse.min.js';
var JSPDF_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
var CHAT_API = '/api/chat';
var DB_NAME = 'tsj_ai_db', DB_STORE = 'conversations', DB_VERSION = 1;

var QUICK_ACTIONS = [
  {label:'Latest Jobs', icon:'briefcase', url:'/section/latest-jobs/'},
  {label:'Results', icon:'trophy', url:'/section/results/'},
  {label:'Admit Card', icon:'id-card', url:'/section/admit-card/'},
  {label:'Answer Key', icon:'file-lines', url:'/section/answer-key/'},
  {label:'State Jobs', icon:'map-location-dot', url:'/state/'},
  {label:'Police Jobs', icon:'shield-halved', url:'/section/police-jobs/'},
  {label:'Railway Jobs', icon:'train', url:'/section/railway-jobs/'},
  {label:'Bank Jobs', icon:'building-columns', url:'/section/bank-jobs/'},
  {label:'Teaching Jobs', icon:'chalkboard-user', url:'/section/teaching-jobs/'},
  {label:'Image Tools', icon:'image', url:'/tools/tools-image.html'},
  {label:'PDF Tools', icon:'file-pdf', url:'/tools/tools-pdf.html'},
  {label:'Video Tools', icon:'video', url:'/tools/tools-audio-video.html'},
];
var SUGGESTED_QUESTIONS = [
  'SSC CGL 2026 ke liye eligibility kya hai?',
  'Railway me 12th pass ke liye konsi jobs hain?',
  '10th pass ke liye latest govt jobs dikhao',
  'Passport size photo kaise banayein?',
];
var TOOL_KEYWORDS = [
  {kw:['resize photo','photo resize','image resize'], label:'Photo Resize Tool', url:'/tools/image/image-resizer.html'},
  {kw:['compress pdf','pdf compress'], label:'PDF Compress Tool', url:'/tools/pdf/compress-pdf.html'},
  {kw:['video compress','compress video'], label:'Video Compress Tool', url:'/tools/av/video-compress.html'},
  {kw:['passport photo','passport size photo'], label:'Passport Photo Tool', url:'/tools/image/passport-photo.html'},
  {kw:['background remove','remove background','bg remove'], label:'Background Remover', url:'/tools/image/background-remove.html'},
  {kw:['photo enhance','enhance photo','upscale photo','photo quality'], label:'AI Photo Enhancer', url:'/tools/image/photo-enhancer.html'},
  {kw:['resume','cv maker','resume banaye'], label:'Resume Maker', url:'/resume-maker/'},
];

/* ============================== STATE ============================== */
var state = {
  open: false,
  fullscreen: false,
  dark: localStorage.getItem('tsj_ai_dark') === '1',
  messages: [],           // {role, content, id, ts}
  searchIndex: null,
  fuse: null,
  streaming: false,
  abortCtrl: null,
  profile: JSON.parse(sessionStorage.getItem('tsj_ai_profile') || '{}'),
  convId: null,
  recognition: null,
  listening: false,
};

/* ============================== UTIL ============================== */
function esc(s){
  return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function uid(){ return 'm'+Date.now().toString(36)+Math.random().toString(36).slice(2,8); }
function $(sel, root){ return (root||document).querySelector(sel); }
function $all(sel, root){ return Array.prototype.slice.call((root||document).querySelectorAll(sel)); }
function loadScript(src){
  return new Promise(function(resolve, reject){
    if(document.querySelector('script[data-tsj-src="'+src+'"]')){ resolve(); return; }
    var s = document.createElement('script');
    s.src = src; s.async = true; s.dataset.tsjSrc = src;
    s.onload = function(){ resolve(); };
    s.onerror = function(){ reject(new Error('load failed: '+src)); };
    document.head.appendChild(s);
  });
}

/* ============================== SAFE MARKDOWN ============================== */
function renderMarkdown(md){
  var html = esc(md);
  // fenced code blocks
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function(m, lang, code){
    return '<pre class="tsj-code"><code>'+code+'</code></pre>';
  });
  // simple pipe tables
  html = html.replace(/((?:^\|.*\|\s*\n)+)/gm, function(block){
    var lines = block.trim().split('\n').filter(Boolean);
    if(lines.length < 2) return block;
    var rows = lines.filter(function(l){ return !/^\|[\s:-]+\|$/.test(l.replace(/-{2,}/g,'-')); });
    var out = '<div class="tsj-tbl-wrap"><table class="tsj-tbl">';
    rows.forEach(function(row, i){
      var cells = row.replace(/^\||\|$/g,'').split('|').map(function(c){ return c.trim(); });
      var tag = i===0 ? 'th' : 'td';
      out += '<tr>' + cells.map(function(c){ return '<'+tag+'>'+c+'</'+tag+'>'; }).join('') + '</tr>';
    });
    out += '</table></div>';
    return out;
  });
  // headers
  html = html.replace(/^### (.*)$/gm, '<h4>$1</h4>');
  html = html.replace(/^## (.*)$/gm, '<h4>$1</h4>');
  html = html.replace(/^# (.*)$/gm, '<h4>$1</h4>');
  // bold / italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
  // inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // links (scheme-restricted, safe) — a topsarkarijobs.com link renders as
  // a distinct button/card (title + open icon) rather than an inline text
  // link, so it reads as "here's the page" instead of blending into prose.
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function(m, text, url){
    if(/^https?:\/\/(www\.)?topsarkarijobs\.com\//i.test(url)){
      return '<a href="'+url+'" target="_blank" rel="noopener noreferrer" class="tsj-cite-btn"><span>'+text+'</span><i class="fa-solid fa-arrow-up-right-from-square"></i></a>';
    }
    return '<a href="'+url+'" target="_blank" rel="noopener noreferrer">'+text+'</a>';
  });
  // bullet lists
  html = html.replace(/^[-*] (.*)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>[\s\S]*?<\/li>\n?)+/g, function(m){ return '<ul>'+m.replace(/\n/g,'')+'</ul>'; });
  // numbered lists
  html = html.replace(/^\d+\. (.*)$/gm, '<li>$1</li>');
  // paragraphs/line breaks
  html = html.split(/\n{2,}/).map(function(p){
    if(/^<(h4|ul|pre|div|table)/.test(p.trim())) return p;
    return '<p>'+p.replace(/\n/g,'<br>')+'</p>';
  }).join('');
  return html;
}

/* ============================== INDEXEDDB (chat history) ============================== */
function idbOpen(){
  return new Promise(function(resolve, reject){
    if(!window.indexedDB){ reject(new Error('no indexeddb')); return; }
    var req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = function(){
      if(!req.result.objectStoreNames.contains(DB_STORE)){
        req.result.createObjectStore(DB_STORE, {keyPath:'id'});
      }
    };
    req.onsuccess = function(){ resolve(req.result); };
    req.onerror = function(){ reject(req.error); };
  });
}
function idbSave(conv){
  return idbOpen().then(function(db){
    return new Promise(function(resolve){
      var tx = db.transaction(DB_STORE, 'readwrite');
      tx.objectStore(DB_STORE).put(conv);
      tx.oncomplete = function(){ resolve(); };
      tx.onerror = function(){ resolve(); };
    });
  }).catch(function(){});
}
function idbLoadLatest(){
  return idbOpen().then(function(db){
    return new Promise(function(resolve){
      var tx = db.transaction(DB_STORE, 'readonly');
      var req = tx.objectStore(DB_STORE).getAll();
      req.onsuccess = function(){
        var all = req.result || [];
        all.sort(function(a,b){ return (b.updatedAt||0)-(a.updatedAt||0); });
        resolve(all[0] || null);
      };
      req.onerror = function(){ resolve(null); };
    });
  }).catch(function(){ return null; });
}

/* ============================== LOCAL SITE SEARCH ============================== */
// Filler words that add noise to a fuzzy match without adding meaning
// ("details batao 2026 ke liye" etc.) — stripped before searching so the
// distinctive terms (place/scheme/org names) carry full weight.
var SEARCH_NOISE_RE = /\b(detail|details|batao|batye|batayein|bataye|please|kya|hai|ka|ki|ke|the|for|about|info|information|update|kare|karo|karein|tell|show|dikhao|puche|puchna|puchein|krna|de|do|dijiye)\b/gi;
// Common Hinglish/Roman-Hindi misspellings of high-frequency government-job
// terms on this site — plain character-fuzzy matching alone scores heavy
// typos like "agrwari" almost as badly as a genuinely-nonexistent query, so
// domain aliases correct the common ones outright before searching.
var SEARCH_ALIASES = [
  [/\b(agrwari|angwanwadi|aganwadi|angawadi|anganwari|aanganwadi|aganvadi)\b/gi, 'anganwadi'],
  [/\bbharti\b/gi, 'recruitment bharti'],
  [/\bbharthi\b/gi, 'recruitment bharti'],
  [/\bnaukri\b/gi, 'job recruitment'],
  [/\bsipahi\b/gi, 'constable'],
  [/\bshikshak\b/gi, 'teacher'],
  [/\bparinam\b/gi, 'result'],
];
function cleanQuery(q){
  var out = String(q||'');
  SEARCH_ALIASES.forEach(function(pair){ out = out.replace(pair[0], pair[1]); });
  out = out.replace(SEARCH_NOISE_RE, ' ').replace(/\b(19|20)\d{2}\b/g, ' ');
  return out.replace(/\s+/g, ' ').trim();
}
function ensureSearchIndex(){
  if(state.fuse) return Promise.resolve(state.fuse);
  return Promise.all([
    fetch(SEARCH_INDEX_URL).then(function(r){ return r.ok ? r.json() : []; }).catch(function(){ return []; }),
    loadScript(FUSE_CDN).catch(function(){}),
  ]).then(function(res){
    state.searchIndex = res[0] || [];
    if(window.Fuse && state.searchIndex.length){
      state.fuse = new window.Fuse(state.searchIndex, {
        keys: [{name:'t', weight:0.7}, {name:'o', weight:0.2}, {name:'c', weight:0.1}],
        threshold: 0.42, ignoreLocation: true, minMatchCharLength: 2, includeScore: true,
      });
    }
    return state.fuse;
  });
}
function localSearch(query){
  if(!state.fuse) return [];
  var cleaned = cleanQuery(query) || query;
  return state.fuse.search(cleaned, {limit: 8}).map(function(r){
    return {title:r.item.t, org:r.item.o, category:r.item.c, date:r.item.d, url:r.item.u, score:r.score, type:r.item.ty};
  });
}
function findToolLink(query){
  var q = query.toLowerCase();
  for(var i=0;i<TOOL_KEYWORDS.length;i++){
    var t = TOOL_KEYWORDS[i];
    for(var j=0;j<t.kw.length;j++){
      if(q.indexOf(t.kw[j]) !== -1) return t;
    }
  }
  return null;
}

/* ============================== PROFILE-BASED JOB FILTER ============================== */
// "Meri age 21 hai aur B.A pass hoon, job batao" style queries need every
// matching job LISTED, not a single fuzzy title match — so instead of Fuse,
// this filters the full index by qualification-category tags ('ql', reused
// from sections-index.json's own classification) and, when stated, the
// user's age against each job's ageLimit range.
var AGE_RE = /\b(?:age|umar|umr)\D{0,6}(\d{2})\b|\b(\d{2})\s*(?:saal|sal|years?|yrs?)(?:\s*(?:ki|ka|old|age))?\b/i;
function extractAge(q){
  var m = AGE_RE.exec(q);
  if(!m) return null;
  var n = parseInt(m[1]||m[2], 10);
  return (n>=14 && n<=70) ? n : null;
}
var QUALIFICATION_PATTERNS = [
  [/\bb\.?\s?a\.?\s*pass\b|(?:^|\s)ba(?:\s|$)/i, ['B_A','Any_Graduate','B_Com']],
  [/\bb\.?\s?com\b/i, ['B_Com','Any_Graduate']],
  [/\bb\.?\s?sc\b/i, ['B_Sc','Any_Graduate']],
  [/\bgraduate\b|\bgraduation\b/i, ['Any_Graduate','Any_Bachelors_Degree']],
  [/\bpost.?graduate\b|\bpost.?graduation\b|\bmasters?\b|\bpg\b/i, ['Any_Post_Graduate','Any_Masters_Degree']],
  [/\bb\.?\s?tech\b|\bb\.?\s?e\.?\b|\bengineering\b/i, ['B_Tech_BE']],
  [/\bdiploma\b/i, ['Diploma']],
  [/\biti\b/i, ['ITI']],
  [/\b10th\b|\bmatric\b/i, ['10TH_Pass']],
  [/\b8th\b/i, ['8TH_Pass']],
  [/\b12th\b|\bintermediate\b|\bhsc\b/i, ['12TH_Pass','Intermediate']],
  [/\bmba\b|\bpgdm\b/i, ['MBA_PGDM']],
  [/\bmca\b/i, ['MCA']],
  [/\bbca\b/i, ['BCA']],
  [/\bllb\b/i, ['LLB']],
  [/\bllm\b/i, ['LLM']],
  [/\bb\.?\s?ed\b/i, ['B_Ed']],
  [/\bmbbs\b/i, ['MBBS']],
  [/\bbds\b/i, ['BDS']],
  [/\bm\.?\s?sc\b/i, ['M_Sc']],
  [/\bm\.?\s?com\b/i, ['M_Com']],
  [/\bm\.?\s?a\.?\s*pass\b|(?:^|\s)ma(?:\s|$)/i, ['MA','M_A']],
  [/\bphd\b|\bm\.?\s?phil\b/i, ['MPhil_PhD']],
  [/\bgnm\b/i, ['GNM']],
  [/\banm\b/i, ['ANM']],
];
// Qualification category -> its /section/{slug}/ browse-all hub page
// (matches generate_all.py's FJA_CAT_MAP/SARK_CAT_MAP / build_chat_index.py's
// SECTIONS list) — so a "10th pass job" query surfaces both the individual
// matching jobs AND the category page to browse the full current list.
var QUAL_SECTION_SLUG = {
  '10TH_Pass':'10th-pass-jobs', '8TH_Pass':'8th-pass', '12TH_Pass':'12th-pass-jobs',
  'Diploma':'diploma-jobs', 'ITI':'iti-jobs', 'B_Tech_BE':'btech-jobs',
  'Any_Graduate':'graduation-jobs', 'Any_Post_Graduate':'post-graduation-jobs',
  'B_Com':'ba-pass', 'B_A':'ba-pass',
};
function detectProfileQuery(query){
  var quals = [];
  QUALIFICATION_PATTERNS.forEach(function(pair){
    if(pair[0].test(query)){
      pair[1].forEach(function(k){ if(quals.indexOf(k)===-1) quals.push(k); });
    }
  });
  if(!quals.length) return null;
  return {age: extractAge(query), quals: quals};
}
function profileSearch(profile){
  if(!state.searchIndex) return [];
  var age = profile.age, quals = profile.quals;
  var matches = state.searchIndex.filter(function(it){
    if(it.ty !== 'job' || !it.ql || !it.ql.length) return false;
    var qualHit = false;
    for(var i=0;i<it.ql.length;i++){ if(quals.indexOf(it.ql[i]) !== -1){ qualHit = true; break; } }
    if(!qualHit) return false;
    if(age && it.age && it.age.length===2 && (age < it.age[0] || age > it.age[1])) return false;
    return true;
  });
  matches.sort(function(a,b){ return (b.d||'').localeCompare(a.d||''); });
  var jobResults = matches.slice(0, 18).map(function(it){
    return {title:it.t, org:it.o, category:it.c, date:it.d, url:it.u, type:it.ty};
  });
  var sectionSlugs = [];
  quals.forEach(function(q){
    var slug = QUAL_SECTION_SLUG[q];
    if(slug && sectionSlugs.indexOf(slug) === -1) sectionSlugs.push(slug);
  });
  var sectionResults = sectionSlugs.map(function(slug){
    var found = null;
    for(var i=0;i<state.searchIndex.length;i++){
      var it = state.searchIndex[i];
      if(it.ty === 'section' && it.u === '/section/'+slug+'/'){ found = it; break; }
    }
    return found ? {title:found.t, org:'', category:'Section', date:'', url:found.u, type:'section'} : null;
  }).filter(Boolean);
  return sectionResults.concat(jobResults).slice(0, 20);
}

/* ============================== CSS ============================== */
var CSS = ''+
'#tsj-chat-root{position:fixed;z-index:99990;font-family:"Noto Sans",system-ui,sans-serif}'+
'#tsj-chat-fab{position:fixed;bottom:20px;left:20px;width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#345de6,#7c3aed);box-shadow:0 8px 24px rgba(52,93,230,.4);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#fff;font-size:1.5rem;z-index:99991;transition:transform .2s}'+
// Deliberately bottom-LEFT: the site's existing push-notification bell
// button already owns the bottom-right corner (see tsj-push.js #tsj-bell),
// and the two floating circles were overlapping there.
'#tsj-chat-fab:hover{transform:scale(1.07)}'+
'#tsj-chat-fab .tsj-fab-badge{position:absolute;top:-2px;right:-2px;width:16px;height:16px;background:#10B981;border:2px solid #fff;border-radius:50%}'+
'.tsj-fab-label{position:fixed;bottom:32px;left:88px;z-index:99991;background:#101828;color:#fff;padding:8px 14px;border-radius:10px;font-size:.78rem;font-weight:700;white-space:nowrap;box-shadow:0 6px 20px rgba(0,0,0,.25);animation:tsjLabelIn .3s ease-out}'+
'.tsj-fab-label::after{content:"";position:absolute;left:-6px;bottom:14px;border:6px solid transparent;border-right-color:#101828}'+
'.tsj-fab-label button{background:none;border:none;color:rgba(255,255,255,.6);cursor:pointer;margin-left:8px;font-size:.85rem;vertical-align:middle}'+
'@keyframes tsjLabelIn{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:translateX(0)}}'+
'@media(max-width:480px){.tsj-fab-label{bottom:80px;left:16px;font-size:.72rem}}'+
'#tsj-chat-panel{position:fixed;bottom:92px;left:20px;width:396px;max-width:calc(100vw - 24px);height:620px;max-height:calc(100vh - 120px);background:#fff;border-radius:18px;box-shadow:0 20px 60px rgba(15,23,42,.25);display:none;flex-direction:column;overflow:hidden;z-index:99990;border:1px solid #e5e7eb}'+
'#tsj-chat-panel.open{display:flex}'+
'#tsj-chat-panel.fullscreen{position:fixed;inset:0;width:100%;height:100%;max-width:100%;max-height:100%;border-radius:0;bottom:0;left:0}'+
'html.tsj-dark #tsj-chat-panel{background:#0f172a;border-color:#2a3441;color:#f1f5f9}'+
'.tsj-hd{background:linear-gradient(135deg,#345de6,#7c3aed);color:#fff;padding:14px 16px;display:flex;align-items:center;gap:10px;flex-shrink:0}'+
'.tsj-hd-icon{width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;font-size:1rem}'+
'.tsj-hd-title{font-weight:800;font-size:.95rem;font-family:"Space Grotesk",sans-serif}'+
'.tsj-hd-sub{font-size:.68rem;opacity:.85}'+
'.tsj-hd-btns{margin-left:auto;display:flex;gap:4px}'+
'.tsj-hd-btn{width:30px;height:30px;border-radius:8px;border:none;background:rgba(255,255,255,.15);color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:.8rem}'+
'.tsj-hd-btn:hover{background:rgba(255,255,255,.3)}'+
'.tsj-quick{display:flex;gap:6px;overflow-x:auto;padding:10px 12px;border-bottom:1px solid #e5e7eb;flex-shrink:0;scrollbar-width:none}'+
'html.tsj-dark .tsj-quick{border-color:#2a3441}'+
'.tsj-quick::-webkit-scrollbar{display:none}'+
'.tsj-qbtn{flex-shrink:0;padding:6px 12px;border-radius:20px;background:#eef4ff;color:#345de6;font-size:.74rem;font-weight:700;border:none;cursor:pointer;white-space:nowrap;display:flex;align-items:center;gap:5px}'+
'html.tsj-dark .tsj-qbtn{background:#1c2740;color:#93c5fd}'+
'.tsj-body{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:12px;background:#f8fafc}'+
'html.tsj-dark .tsj-body{background:#0b1220}'+
'.tsj-welcome{text-align:center;padding:18px 10px;color:#6B7280}'+
'.tsj-welcome i{font-size:2rem;color:#345de6;margin-bottom:8px;display:block}'+
'.tsj-sugg{display:flex;flex-direction:column;gap:6px;margin-top:12px}'+
'.tsj-sugg-btn{text-align:left;padding:9px 12px;border-radius:10px;border:1.5px solid #e5e7eb;background:#fff;font-size:.8rem;cursor:pointer;color:#101828}'+
'html.tsj-dark .tsj-sugg-btn{background:#151f33;border-color:#2a3441;color:#f1f5f9}'+
'.tsj-sugg-btn:hover{border-color:#345de6}'+
'.tsj-msg{display:flex;gap:8px;max-width:100%}'+
'.tsj-msg.user{flex-direction:row-reverse}'+
'.tsj-avatar{width:26px;height:26px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:.7rem;color:#fff}'+
'.tsj-msg.user .tsj-avatar{background:#6B7280}'+
'.tsj-msg.assistant .tsj-avatar{background:linear-gradient(135deg,#345de6,#7c3aed)}'+
'.tsj-bubble{padding:10px 13px;border-radius:14px;font-size:.86rem;line-height:1.6;max-width:82%;overflow-wrap:break-word}'+
'.tsj-msg.user .tsj-bubble{background:#345de6;color:#fff;border-bottom-right-radius:4px}'+
'.tsj-msg.assistant .tsj-bubble{background:#fff;color:#101828;border:1px solid #e5e7eb;border-bottom-left-radius:4px}'+
'html.tsj-dark .tsj-msg.assistant .tsj-bubble{background:#151f33;color:#f1f5f9;border-color:#2a3441}'+
'.tsj-bubble p{margin:0 0 8px}.tsj-bubble p:last-child{margin-bottom:0}'+
'.tsj-bubble h4{font-size:.88rem;margin:8px 0 4px;font-family:"Space Grotesk",sans-serif}'+
'.tsj-bubble ul{margin:4px 0 8px 18px;padding:0}'+
'.tsj-bubble li{margin-bottom:3px}'+
'.tsj-bubble code{background:rgba(0,0,0,.06);padding:1px 5px;border-radius:4px;font-size:.82em}'+
'.tsj-bubble pre.tsj-code{background:#1e293b;color:#e2e8f0;padding:10px;border-radius:8px;overflow-x:auto;margin:6px 0;font-size:.78rem}'+
'.tsj-bubble pre.tsj-code code{background:none;padding:0}'+
'.tsj-tbl-wrap{overflow-x:auto;margin:6px 0}'+
'.tsj-tbl{border-collapse:collapse;width:100%;font-size:.78rem}'+
'.tsj-tbl th,.tsj-tbl td{border:1px solid #e5e7eb;padding:5px 8px;text-align:left}'+
'html.tsj-dark .tsj-tbl th,html.tsj-dark .tsj-tbl td{border-color:#2a3441}'+
'.tsj-tbl th{background:#f1f5f9;font-weight:700}'+
'html.tsj-dark .tsj-tbl th{background:#1c2740}'+
'.tsj-bubble a{color:#345de6;text-decoration:underline}'+
'.tsj-msg.user .tsj-bubble a{color:#dbe6ff}'+
'.tsj-bubble p:has(> a.tsj-cite-btn:only-child){margin:6px 0}'+
'.tsj-cite-btn{display:flex!important;align-items:center;gap:8px;background:#eef4ff;color:#1d4ed8!important;text-decoration:none!important;font-weight:700;font-size:.82rem;padding:10px 12px;border-radius:10px;border:1px solid #dbe6ff}'+
'.tsj-cite-btn:hover{background:#dbe6ff}'+
'.tsj-cite-btn span{flex:1}'+
'.tsj-cite-btn i{flex-shrink:0;font-size:.74rem;opacity:.7}'+
'html.tsj-dark .tsj-cite-btn{background:#1c2740;color:#93c5fd!important;border-color:#2a3441}'+
'html.tsj-dark .tsj-cite-btn:hover{background:#243254}'+
// Explicit row/nowrap + !important: this widget's CSS is appended after the
// site's own stylesheets, and a generic site-wide button/flex rule was
// winning the cascade and stacking these vertically instead of in a row.
'.tsj-actions{display:flex!important;flex-direction:row!important;flex-wrap:nowrap!important;align-items:center!important;gap:4px;margin-top:4px;padding-left:34px}'+
'.tsj-act-btn{width:24px;height:24px;flex-shrink:0;border:none;background:none;color:#9CA3AF;cursor:pointer;font-size:.72rem;border-radius:5px;display:flex!important;flex-direction:row!important;align-items:center;justify-content:center}'+
'.tsj-act-btn:hover{background:#eef4ff;color:#345de6}'+
'.tsj-act-btn.active{color:#345de6}'+
'.tsj-cursor{display:inline-block;width:7px;height:14px;background:#345de6;margin-left:2px;animation:tsjblink 1s step-start infinite;vertical-align:middle}'+
'@keyframes tsjblink{50%{opacity:0}}'+
'.tsj-typing{display:flex;gap:4px;padding:4px 0}'+
'.tsj-typing span{width:7px;height:7px;border-radius:50%;background:#9CA3AF;animation:tsjbounce 1.2s infinite ease-in-out}'+
'.tsj-typing span:nth-child(2){animation-delay:.15s}.tsj-typing span:nth-child(3){animation-delay:.3s}'+
'@keyframes tsjbounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-5px)}}'+
'.tsj-input-wrap{padding:10px 12px;border-top:1px solid #e5e7eb;flex-shrink:0;background:#fff}'+
'html.tsj-dark .tsj-input-wrap{background:#0f172a;border-color:#2a3441}'+
'.tsj-input-row{display:flex;align-items:flex-end;gap:6px;background:#f1f5f9;border-radius:14px;padding:6px 6px 6px 12px;border:1.5px solid transparent}'+
'.tsj-input-row:focus-within{border-color:#345de6}'+
'html.tsj-dark .tsj-input-row{background:#151f33}'+
'#tsj-input{flex:1;border:none;background:none;resize:none;font-size:.86rem;font-family:inherit;max-height:100px;outline:none;padding:6px 0;color:#101828}'+
'html.tsj-dark #tsj-input{color:#f1f5f9}'+
'.tsj-input-btn{width:34px;height:34px;border-radius:50%;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:.9rem}'+
'.tsj-mic-btn{background:none;color:#6B7280}'+
'.tsj-mic-btn.listening{color:#EF4444;animation:tsjpulse 1s infinite}'+
'@keyframes tsjpulse{50%{opacity:.5}}'+
'.tsj-send-btn{background:#345de6;color:#fff}'+
'.tsj-send-btn:disabled{opacity:.4;cursor:not-allowed}'+
'.tsj-footer-links{display:flex;justify-content:center;gap:12px;padding:6px 0 2px;font-size:.68rem;color:#9CA3AF}'+
'.tsj-footer-links button{background:none;border:none;color:#9CA3AF;cursor:pointer;font-size:.68rem;text-decoration:underline}'+
/* Site's mobile bottom tab bar (.mobile-bottom-bar) shows under this same
   900px breakpoint — the fab must clear it or it sits on top of the "Home"
   tab. --tsj-nav-h is measured live from the real element (syncNavOffset())
   since its rendered height varies by page/device and doesn't match a
   single hardcoded guess; the var()'s 72px fallback covers pages where the
   bar hasn't been measured yet. */
'@media(max-width:900px){'+
'#tsj-chat-fab{bottom:calc(var(--tsj-nav-h,72px) + 10px)}'+
'.tsj-fab-label{bottom:calc(var(--tsj-nav-h,72px) + 22px)}'+
'#tsj-chat-panel{bottom:calc(var(--tsj-nav-h,72px) + 82px)}'+
'}'+
'@media(max-width:480px){'+
'#tsj-chat-panel{right:8px;left:8px;width:auto;bottom:0;height:82vh;max-height:82vh;border-radius:16px 16px 0 0}'+
'}'+
'.tsj-profile-card{background:#eef4ff;border-radius:10px;padding:10px;font-size:.78rem;margin-bottom:8px}'+
'html.tsj-dark .tsj-profile-card{background:#1c2740}'+
'.tsj-profile-row{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}'+
'.tsj-profile-row select,.tsj-profile-row input{flex:1;min-width:80px;padding:5px 7px;border-radius:6px;border:1px solid #d1d5db;font-size:.76rem}';

/* ============================== HTML ============================== */
function buildHTML(){
  var quickHtml = QUICK_ACTIONS.map(function(q){
    return '<button class="tsj-qbtn" data-url="'+esc(q.url)+'"><i class="fa-solid fa-'+q.icon+'"></i> '+esc(q.label)+'</button>';
  }).join('');
  var suggHtml = SUGGESTED_QUESTIONS.map(function(q){
    return '<button class="tsj-sugg-btn" data-q="'+esc(q)+'">'+esc(q)+'</button>';
  }).join('');

  var root = document.createElement('div');
  root.id = 'tsj-chat-root';
  root.innerHTML =
    '<button id="tsj-chat-fab" aria-label="Open TSJ AI — AI assistant to help you find the best government job for you" aria-expanded="false"><i class="fa-solid fa-robot"></i><span class="tsj-fab-badge"></span></button>'+
    '<div class="tsj-fab-label" id="tsj-fab-label" role="status">🎯 <strong>TSJ AI</strong> — Aapke liye Best Government Job Dhundhne mein Help karega!<button id="tsj-fab-label-close" aria-label="Dismiss">&times;</button></div>'+
    '<div id="tsj-chat-panel" role="dialog" aria-label="TSJ AI Assistant chat">'+
      '<div class="tsj-hd">'+
        '<div class="tsj-hd-icon"><i class="fa-solid fa-robot"></i></div>'+
        '<div><div class="tsj-hd-title">TSJ AI</div><div class="tsj-hd-sub">Your Smart Government Job Assistant</div></div>'+
        '<div class="tsj-hd-btns">'+
          '<button class="tsj-hd-btn" id="tsj-dark-toggle" aria-label="Toggle dark mode"><i class="fa-solid fa-moon"></i></button>'+
          '<button class="tsj-hd-btn" id="tsj-export-btn" aria-label="Export chat"><i class="fa-solid fa-download"></i></button>'+
          '<button class="tsj-hd-btn" id="tsj-clear-btn" aria-label="Clear chat"><i class="fa-solid fa-broom"></i></button>'+
          '<button class="tsj-hd-btn" id="tsj-fullscreen-btn" aria-label="Fullscreen"><i class="fa-solid fa-expand"></i></button>'+
          '<button class="tsj-hd-btn" id="tsj-close-btn" aria-label="Close chat"><i class="fa-solid fa-xmark"></i></button>'+
        '</div>'+
      '</div>'+
      '<div class="tsj-quick" id="tsj-quick">'+quickHtml+'</div>'+
      '<div class="tsj-body" id="tsj-body">'+
        '<div class="tsj-welcome" id="tsj-welcome">'+
          '<i class="fa-solid fa-hand-sparkles"></i>'+
          '<div style="font-weight:800;font-size:.95rem;color:#101828" id="tsj-welcome-title">Namaste! Main TSJ AI hoon 👋</div>'+
          '<div style="font-size:.8rem;margin-top:4px">Koi bhi government job sawaal poochein — vacancy, eligibility, exam pattern, admit card, kuch bhi.</div>'+
          '<div class="tsj-sugg">'+suggHtml+'</div>'+
        '</div>'+
      '</div>'+
      '<div class="tsj-input-wrap">'+
        '<div class="tsj-input-row">'+
          '<textarea id="tsj-input" placeholder="Apna sawaal likhein... (Hindi ya English)" rows="1" aria-label="Type your question"></textarea>'+
          '<button class="tsj-input-btn tsj-mic-btn" id="tsj-mic-btn" aria-label="Voice input" title="Voice input"><i class="fa-solid fa-microphone"></i></button>'+
          '<button class="tsj-input-btn tsj-send-btn" id="tsj-send-btn" aria-label="Send message"><i class="fa-solid fa-paper-plane"></i></button>'+
        '</div>'+
        '<div class="tsj-footer-links">'+
          '<button id="tsj-profile-btn">My Profile</button>'+
          '<span>·</span><span>Powered by Groq AI</span>'+
        '</div>'+
      '</div>'+
    '</div>';
  document.body.appendChild(root);
}

/* ============================== RENDER MESSAGES ============================== */
function scrollToBottom(){
  var body = $('#tsj-body');
  body.scrollTop = body.scrollHeight;
}
function renderMessage(msg){
  var welcome = $('#tsj-welcome');
  if(welcome) welcome.style.display = 'none';
  var body = $('#tsj-body');
  var wrap = document.createElement('div');
  wrap.className = 'tsj-msg-wrap';
  wrap.dataset.id = msg.id;
  var avatarIcon = msg.role === 'user' ? 'fa-user' : 'fa-robot';
  wrap.innerHTML =
    '<div class="tsj-msg '+msg.role+'">'+
      '<div class="tsj-avatar"><i class="fa-solid '+avatarIcon+'"></i></div>'+
      '<div class="tsj-bubble" id="bubble-'+msg.id+'">'+renderMarkdown(msg.content)+'</div>'+
    '</div>'+
    (msg.role==='assistant' ? actionsHtml(msg.id) : '');
  body.appendChild(wrap);
  scrollToBottom();
  return wrap;
}
function actionsHtml(id){
  return '<div class="tsj-actions" data-for="'+id+'">'+
    '<button class="tsj-act-btn" data-act="copy" title="Copy"><i class="fa-solid fa-copy"></i></button>'+
    '<button class="tsj-act-btn" data-act="speak" title="Read aloud"><i class="fa-solid fa-volume-high"></i></button>'+
    '<button class="tsj-act-btn" data-act="like" title="Like"><i class="fa-solid fa-thumbs-up"></i></button>'+
    '<button class="tsj-act-btn" data-act="dislike" title="Dislike"><i class="fa-solid fa-thumbs-down"></i></button>'+
    '<button class="tsj-act-btn" data-act="regenerate" title="Regenerate"><i class="fa-solid fa-rotate"></i></button>'+
  '</div>';
}
function renderTyping(){
  var body = $('#tsj-body');
  var el = document.createElement('div');
  el.className = 'tsj-msg-wrap'; el.id = 'tsj-typing-wrap';
  el.innerHTML = '<div class="tsj-msg assistant"><div class="tsj-avatar"><i class="fa-solid fa-robot"></i></div>'+
    '<div class="tsj-bubble"><div class="tsj-typing"><span></span><span></span><span></span></div></div></div>';
  body.appendChild(el);
  scrollToBottom();
}
function removeTyping(){
  var el = $('#tsj-typing-wrap');
  if(el) el.remove();
}

/* ============================== CHAT SEND FLOW ============================== */
function saveConversation(){
  if(!state.convId) state.convId = uid();
  idbSave({id: state.convId, messages: state.messages, updatedAt: Date.now()});
}

function detectNeedsWebSearch(query, siteMatches){
  // No local match at all -> definitely worth a live search.
  if(siteMatches.length === 0) return true;
  // Character-fuzzy scoring can't reliably tell "correct match with a heavy
  // typo" apart from "nothing real matched, here's the least-bad guess" —
  // both score poorly. Rather than silently trusting (or discarding) a
  // shaky match, also fetch live results as a second opinion; the model
  // sees both and picks whichever actually answers the question.
  var best = siteMatches[0].score;
  return typeof best === 'number' && best > 0.3;
}

async function sendMessage(text){
  text = String(text||'').trim();
  if(!text || state.streaming) return;
  if(text.length > 2000){ text = text.slice(0,2000); }

  var toolMatch = findToolLink(text);

  var userMsg = {id: uid(), role:'user', content: text, ts: Date.now()};
  state.messages.push(userMsg);
  renderMessage(userMsg);
  $('#tsj-input').value = '';
  autoGrow($('#tsj-input'));
  saveConversation();

  await ensureSearchIndex();
  var profileQuery = detectProfileQuery(text);
  var profileMatches = profileQuery ? profileSearch(profileQuery) : [];
  var siteMatches = profileMatches.length ? profileMatches : localSearch(text);
  if(!profileMatches.length && toolMatch){
    // Let the AI itself know about the deep-link too (not just the button
    // rendered after streaming), so it can mention/cite it if relevant.
    siteMatches = [{title:toolMatch.label, org:'', category:'Tool', date:'', url:toolMatch.url, type:'tool'}].concat(siteMatches).slice(0,8);
  }
  var needsWebSearch = profileMatches.length ? false : detectNeedsWebSearch(text, siteMatches);

  renderTyping();
  state.streaming = true;
  updateSendButton();

  var asstMsg = {id: uid(), role:'assistant', content:'', ts: Date.now()};
  var bubbleEl = null;
  var fullText = '';

  var payload = {
    messages: state.messages.map(function(m){ return {role:m.role, content:m.content}; }),
    siteMatches: siteMatches,
    needsWebSearch: needsWebSearch,
    profile: state.profile,
    profileQuery: profileMatches.length ? profileQuery : null,
  };

  try{
    var ctrl = new AbortController();
    state.abortCtrl = ctrl;
    var res = await fetch(CHAT_API, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload), signal: ctrl.signal,
    });
    if(!res.ok){
      var errBody = await res.json().catch(function(){ return {}; });
      throw new Error(errBody.error || ('HTTP '+res.status));
    }
    removeTyping();
    var wrap = renderMessage(asstMsg);
    bubbleEl = $('#bubble-'+asstMsg.id);
    bubbleEl.innerHTML = '<span class="tsj-stream-txt"></span><span class="tsj-cursor"></span>';
    var streamTxt = bubbleEl.querySelector('.tsj-stream-txt');

    var reader = res.body.getReader();
    var decoder = new TextDecoder();
    var buf = '';
    while(true){
      var chunk = await reader.read();
      if(chunk.done) break;
      buf += decoder.decode(chunk.value, {stream:true});
      var lines = buf.split('\n');
      buf = lines.pop();
      for(var i=0;i<lines.length;i++){
        var line = lines[i].trim();
        if(!line.indexOf('data:')===0 || line.slice(0,5)!=='data:') continue;
        var data = line.slice(5).trim();
        if(data === '[DONE]') continue;
        try{
          var json = JSON.parse(data);
          var delta = json.choices && json.choices[0] && json.choices[0].delta && json.choices[0].delta.content;
          if(delta){
            fullText += delta;
            streamTxt.textContent = fullText;
            scrollToBottom();
          }
        }catch(e){}
      }
    }
    bubbleEl.innerHTML = renderMarkdown(fullText || '(No response)');
    asstMsg.content = fullText || '(No response)';
    // Note: the action buttons (copy/speak/like/etc) were already appended
    // by the initial renderMessage(asstMsg) call above — no need to add them
    // again here, that would just duplicate the button row.
    state.messages.push(asstMsg);
    saveConversation();
  }catch(e){
    removeTyping();
    if(e.name !== 'AbortError'){
      var errMsg = {id: uid(), role:'assistant', content: 'Sorry, kuch gadbad ho gayi: '+esc(String(e.message||e)).slice(0,200)+'. Thodi der baad try karein.', ts: Date.now()};
      renderMessage(errMsg);
      state.messages.push(errMsg);
    }
  }finally{
    state.streaming = false;
    state.abortCtrl = null;
    updateSendButton();
  }

  if(toolMatch){
    var toolEl = document.createElement('div');
    toolEl.className = 'tsj-msg-wrap';
    toolEl.innerHTML = '<div style="padding-left:34px;margin-top:-4px"><a href="'+esc(toolMatch.url)+'" class="tsj-qbtn" style="text-decoration:none;display:inline-flex"><i class="fa-solid fa-wrench"></i> Open '+esc(toolMatch.label)+'</a></div>';
    $('#tsj-body').appendChild(toolEl);
    scrollToBottom();
  }
}

function updateSendButton(){
  var btn = $('#tsj-send-btn');
  if(!btn) return;
  btn.innerHTML = state.streaming ? '<i class="fa-solid fa-stop"></i>' : '<i class="fa-solid fa-paper-plane"></i>';
}

function autoGrow(el){
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}

/* ============================== VOICE ============================== */
function initVoice(){
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!SR) return;
  var rec = new SR();
  rec.continuous = false;
  rec.interimResults = false;
  rec.onresult = function(e){
    var text = e.results[0][0].transcript;
    $('#tsj-input').value = text;
    autoGrow($('#tsj-input'));
    sendMessage(text);
  };
  rec.onend = function(){ state.listening = false; $('#tsj-mic-btn').classList.remove('listening'); };
  rec.onerror = function(){ state.listening = false; $('#tsj-mic-btn').classList.remove('listening'); };
  state.recognition = rec;
}
function toggleListening(){
  if(!state.recognition){ tsjToast('Voice input is not supported in this browser.'); return; }
  if(state.listening){ state.recognition.stop(); state.listening = false; $('#tsj-mic-btn').classList.remove('listening'); return; }
  var lang = /[ऀ-ॿ]/.test($('#tsj-input').value) ? 'hi-IN' : 'en-IN';
  state.recognition.lang = lang;
  try{ state.recognition.start(); state.listening = true; $('#tsj-mic-btn').classList.add('listening'); }
  catch(e){}
}
function speakText(text, btn){
  if(!window.speechSynthesis){ tsjToast('Voice output not supported.'); return; }
  if(window.speechSynthesis.speaking){
    window.speechSynthesis.cancel();
    if(btn) btn.classList.remove('active');
    return;
  }
  var plain = text.replace(/<[^>]+>/g,'').replace(/[#*`_]/g,'');
  var utter = new SpeechSynthesisUtterance(plain.slice(0, 600));
  utter.lang = /[ऀ-ॿ]/.test(plain) ? 'hi-IN' : 'en-IN';
  if(btn){
    btn.classList.add('active');
    utter.onend = function(){ btn.classList.remove('active'); };
  }
  window.speechSynthesis.speak(utter);
}

/* ============================== TOAST ============================== */
function tsjToast(msg){
  var t = document.getElementById('tsj-toast-el');
  if(!t){
    t = document.createElement('div');
    t.id = 'tsj-toast-el';
    t.style.cssText = 'position:fixed;bottom:100px;right:20px;background:#101828;color:#fff;padding:9px 16px;border-radius:9px;font-size:.8rem;z-index:99999;box-shadow:0 6px 20px rgba(0,0,0,.3);opacity:0;transition:opacity .2s;font-family:sans-serif;max-width:280px';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.opacity = '1';
  clearTimeout(t._h);
  t._h = setTimeout(function(){ t.style.opacity = '0'; }, 2800);
}

/* ============================== EXPORT ============================== */
function exportTxt(){
  var lines = state.messages.map(function(m){ return (m.role==='user'?'You: ':'TSJ AI: ')+m.content; });
  var blob = new Blob([lines.join('\n\n')], {type:'text/plain'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'tsj-ai-chat.txt';
  document.body.appendChild(a); a.click(); a.remove();
}
function exportPdf(){
  loadScript(JSPDF_CDN).then(function(){
    var jsPDFCtor = window.jspdf && window.jspdf.jsPDF;
    if(!jsPDFCtor){ tsjToast('PDF export failed to load — try TXT export instead.'); return; }
    var doc = new jsPDFCtor();
    var y = 15;
    doc.setFontSize(14); doc.text('TSJ AI — Chat Export', 10, y); y+=8;
    doc.setFontSize(10);
    state.messages.forEach(function(m){
      var prefix = (m.role==='user'?'You: ':'TSJ AI: ');
      var text = doc.splitTextToSize(prefix + m.content.replace(/[#*`_]/g,''), 190);
      text.forEach(function(line){
        if(y > 280){ doc.addPage(); y = 15; }
        doc.text(line, 10, y); y += 5.5;
      });
      y += 3;
    });
    doc.save('tsj-ai-chat.pdf');
  }).catch(function(){ tsjToast('PDF export failed to load — try TXT export instead.'); });
}

/* ============================== PROFILE ============================== */
function showProfileForm(){
  var p = state.profile;
  var body = $('#tsj-body');
  var el = document.createElement('div');
  el.className = 'tsj-msg-wrap';
  el.innerHTML = '<div class="tsj-profile-card">'+
    '<div style="font-weight:800">Aapki details (behtar suggestions ke liye)</div>'+
    '<div class="tsj-profile-row">'+
      '<select id="tsj-p-qual"><option value="">Qualification</option>'+
      ['10th','12th','ITI','Diploma','Graduate','Post Graduate'].map(function(q){ return '<option '+(p.qualification===q?'selected':'')+'>'+q+'</option>'; }).join('')+
      '</select>'+
      '<input id="tsj-p-age" type="number" placeholder="Age" value="'+esc(p.age||'')+'" min="15" max="65">'+
    '</div>'+
    '<div class="tsj-profile-row">'+
      '<input id="tsj-p-state" type="text" placeholder="State" value="'+esc(p.state||'')+'">'+
      '<select id="tsj-p-cat"><option value="">Category</option>'+
      ['General','OBC','SC','ST','EWS'].map(function(c){ return '<option '+(p.category===c?'selected':'')+'>'+c+'</option>'; }).join('')+
      '</select>'+
    '</div>'+
    '<button class="tsj-sugg-btn" id="tsj-p-save" style="margin-top:8px;text-align:center;font-weight:700;border-color:#345de6;color:#345de6">Save &amp; Get Best Jobs</button>'+
  '</div>';
  body.appendChild(el);
  scrollToBottom();
  $('#tsj-p-save').addEventListener('click', function(){
    state.profile = {
      qualification: $('#tsj-p-qual').value, age: $('#tsj-p-age').value,
      state: $('#tsj-p-state').value, category: $('#tsj-p-cat').value,
    };
    sessionStorage.setItem('tsj_ai_profile', JSON.stringify(state.profile));
    el.remove();
    sendMessage('Mere profile (Qualification: '+(state.profile.qualification||'N/A')+', Age: '+(state.profile.age||'N/A')+', State: '+(state.profile.state||'N/A')+', Category: '+(state.profile.category||'N/A')+') ke hisab se best matching government jobs suggest karein.');
  });
}

/* ============================== FAB DISCOVERY LABEL ============================== */
function dismissFabLabel(){
  var label = $('#tsj-fab-label');
  if(label) label.remove();
  sessionStorage.setItem('tsj_ai_label_seen', '1');
}
function maybeShowFabLabel(){
  if(sessionStorage.getItem('tsj_ai_label_seen')){
    var label = $('#tsj-fab-label');
    if(label) label.remove();
    return;
  }
  setTimeout(function(){
    var btn = $('#tsj-fab-label-close');
    if(btn) btn.addEventListener('click', function(e){ e.stopPropagation(); dismissFabLabel(); });
  }, 0);
  // Auto-dismiss after a while so it doesn't nag returning visitors mid-session.
  setTimeout(dismissFabLabel, 9000);
}

/* ============================== EVENT WIRING ============================== */
function openPanel(){
  state.open = true;
  dismissFabLabel();
  $('#tsj-chat-panel').classList.add('open');
  $('#tsj-chat-fab').setAttribute('aria-expanded','true');
  setTimeout(function(){ $('#tsj-input').focus(); }, 100);
  ensureSearchIndex();
  if(!state.recognition) initVoice();
}
function closePanel(){
  state.open = false;
  $('#tsj-chat-panel').classList.remove('open');
  $('#tsj-chat-fab').setAttribute('aria-expanded','false');
}
function applyDarkMode(){
  document.documentElement.classList.toggle('tsj-dark', state.dark);
}

function wireEvents(){
  $('#tsj-chat-fab').addEventListener('click', function(){
    state.open ? closePanel() : openPanel();
  });
  $('#tsj-close-btn').addEventListener('click', closePanel);
  $('#tsj-dark-toggle').addEventListener('click', function(){
    state.dark = !state.dark;
    localStorage.setItem('tsj_ai_dark', state.dark ? '1':'0');
    applyDarkMode();
  });
  $('#tsj-fullscreen-btn').addEventListener('click', function(){
    state.fullscreen = !state.fullscreen;
    $('#tsj-chat-panel').classList.toggle('fullscreen', state.fullscreen);
  });
  $('#tsj-clear-btn').addEventListener('click', function(){
    if(!confirm('Clear this chat?')) return;
    state.messages = [];
    state.convId = uid();
    $('#tsj-body').innerHTML = '';
    var w = $('#tsj-welcome');
    if(w){ $('#tsj-body').appendChild(w); w.style.display=''; }
  });
  $('#tsj-export-btn').addEventListener('click', function(){
    if(!state.messages.length){ tsjToast('No messages to export yet.'); return; }
    var choice = confirm('Click OK to export as PDF, Cancel for TXT.');
    choice ? exportPdf() : exportTxt();
  });
  $('#tsj-profile-btn').addEventListener('click', showProfileForm);
  $('#tsj-mic-btn').addEventListener('click', toggleListening);

  $('#tsj-send-btn').addEventListener('click', function(){
    if(state.streaming){
      if(state.abortCtrl) state.abortCtrl.abort();
      return;
    }
    sendMessage($('#tsj-input').value);
  });
  $('#tsj-input').addEventListener('keydown', function(e){
    if(e.key==='Enter' && !e.shiftKey){
      e.preventDefault();
      if(!state.streaming) sendMessage($('#tsj-input').value);
    }
    if(e.key==='Escape') closePanel();
  });
  $('#tsj-input').addEventListener('input', function(){ autoGrow(this); });

  $('#tsj-quick').addEventListener('click', function(e){
    var btn = e.target.closest('.tsj-qbtn');
    if(btn) window.location.href = btn.dataset.url;
  });
  $('#tsj-body').addEventListener('click', function(e){
    var sugg = e.target.closest('.tsj-sugg-btn');
    if(sugg && sugg.dataset.q){ sendMessage(sugg.dataset.q); return; }
    var act = e.target.closest('.tsj-act-btn');
    if(act){
      var id = act.closest('.tsj-actions').dataset.for;
      var msg = state.messages.find(function(m){ return m.id===id; });
      if(!msg) return;
      var action = act.dataset.act;
      if(action==='copy'){
        navigator.clipboard.writeText(msg.content).then(function(){ tsjToast('Copied ✓'); });
      }else if(action==='speak'){
        speakText(msg.content, act);
      }else if(action==='like'){
        act.classList.toggle('active');
        var dis = act.parentElement.querySelector('[data-act="dislike"]');
        if(dis) dis.classList.remove('active');
      }else if(action==='dislike'){
        act.classList.toggle('active');
        var lk = act.parentElement.querySelector('[data-act="like"]');
        if(lk) lk.classList.remove('active');
      }else if(action==='regenerate'){
        var idx = state.messages.findIndex(function(m){ return m.id===id; });
        var priorUser = null, priorUserIdx = -1;
        for(var i=idx-1;i>=0;i--){ if(state.messages[i].role==='user'){ priorUser = state.messages[i]; priorUserIdx = i; break; } }
        if(priorUser){
          // Drop both the assistant reply being regenerated AND the user
          // message that prompted it (from state AND the DOM) — sendMessage()
          // below re-creates a fresh user message + bubble on its own, so
          // leaving the old ones in place would show a duplicate question.
          state.messages = state.messages.slice(0, priorUserIdx);
          $('[data-id="'+id+'"]', document).remove();
          $('[data-id="'+priorUser.id+'"]', document).remove();
          sendMessage(priorUser.content);
        }
      }
    }
  });

  document.addEventListener('keydown', function(e){
    if(e.key==='Escape' && state.open) closePanel();
  });
}

/* The site's mobile bottom tab bar's actual rendered height varies by page
   (font metrics can push it past its own CSS's nominal min-height) — measure
   it directly rather than trusting a hardcoded guess, which was found to
   still overlap the fab on real devices. */
function syncNavOffset(){
  var nav = document.querySelector('.mobile-bottom-bar');
  if(nav && nav.offsetHeight){
    document.documentElement.style.setProperty('--tsj-nav-h', nav.offsetHeight + 'px');
  }
}

/* ============================== INIT ============================== */
function init(){
  buildHTML();
  var style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);
  applyDarkMode();
  wireEvents();
  syncNavOffset();
  // On generate_all.py pages the bottom bar comes from header.html, fetched
  // and injected asynchronously by tsj-init.js — it may not exist yet at
  // DOMContentLoaded, so re-check a few times until it shows up.
  [100, 400, 1000, 2000, 4000].forEach(function(ms){ setTimeout(syncNavOffset, ms); });
  window.addEventListener('resize', syncNavOffset);
  window.addEventListener('orientationchange', syncNavOffset);
  maybeShowFabLabel();
  idbLoadLatest().then(function(conv){
    if(conv && conv.messages && conv.messages.length){
      state.messages = conv.messages;
      state.convId = conv.id;
      state.messages.forEach(function(m){ renderMessage(m); });
    }
  });
}

if(document.readyState === 'loading'){
  document.addEventListener('DOMContentLoaded', init);
}else{
  init();
}
})();
