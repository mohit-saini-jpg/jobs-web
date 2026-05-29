/**
 * preferred-source-renderer.js v6.0
 * TOP SARKARI JOBS — Master Render Coordinator
 * =============================================
 * ROLE: Guard + Coordinator only. Does NOT render independently.
 * 1. Prevents duplicate sections
 * 2. Adds "Set as Preferred Source" card
 * 3. Updates Quick Highlights with real data
 * 4. SEO tag updater
 * 5. Internal link rewriter
 */
(function () {
  'use strict';
  if (window.__TSJ_PSR_V6_DONE) return;
  window.__TSJ_PSR_V6_DONE = true;

  var SITE = 'https://www.topsarkarijobs.com';

  function esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  /* § 1 — DUPLICATE SECTION GUARD */
  function removeDuplicateSections() {
    var seen = {};
    document.querySelectorAll('.udyn-card').forEach(function(card) {
      var head = card.querySelector('.udyn-head');
      if (!head) return;
      var key = head.textContent.trim().toLowerCase().replace(/\s+/g,' ');
      if (seen[key]) { card.remove(); } else { seen[key] = true; }
    });
  }

  /* § 2 — PREFERRED SOURCE CARD */
  function renderPreferredSourceCard(job) {
    var card = document.getElementById('preferredSourceCard');
    if (!card) return;
    var bd = job.basic_details || {};
    var dates = job.important_dates || {};
    var org   = bd.organization_name || bd.post_name || job.organization || '';
    var posts = bd.total_vacancies || bd.total_vacancy || job.total_vacancy || job.vacancies || '';
    var ld    = dates.last_date_to_apply || dates.last_date || dates.application_end_date || job.lastDate || job.last_date || '';
    var mode  = bd.application_mode || job.apply_mode || job.applyMode || '';
    var qual  = '';
    var qd = job.qualification || {};
    if (typeof qd === 'string') qual = qd.slice(0,120);
    else if (qd && qd.essential_qualification) qual = String(qd.essential_qualification).slice(0,120);
    else if (qd && qd.qualification) qual = String(qd.qualification).slice(0,120);

    if (ld) {
      var dm = ld.match(/^(\d{4})-(\d{2})-(\d{2})/);
      if (dm) ld = dm[3]+'/'+dm[2]+'/'+dm[1];
    }

    var rows = '';
    if (org)   rows += '<tr><td style="padding:6px 10px;font-size:.8rem;color:#64748b;white-space:nowrap">Organisation</td><td style="padding:6px 10px;font-size:.82rem;font-weight:700">'+esc(org)+'</td></tr>';
    if (posts) rows += '<tr><td style="padding:6px 10px;font-size:.8rem;color:#64748b;white-space:nowrap">Total Posts</td><td style="padding:6px 10px;font-size:.82rem;font-weight:700">'+esc(String(posts))+'</td></tr>';
    if (ld)    rows += '<tr><td style="padding:6px 10px;font-size:.8rem;color:#64748b;white-space:nowrap">Last Date</td><td style="padding:6px 10px;font-size:.82rem;font-weight:700;color:#dc2626">'+esc(ld)+'</td></tr>';
    else       rows += '<tr><td style="padding:6px 10px;font-size:.8rem;color:#64748b">Last Date</td><td style="padding:6px 10px;font-size:.82rem">See Notification</td></tr>';
    if (mode)  rows += '<tr><td style="padding:6px 10px;font-size:.8rem;color:#64748b">Apply Mode</td><td style="padding:6px 10px;font-size:.82rem;font-weight:700">'+esc(mode)+'</td></tr>';
    if (qual)  rows += '<tr><td style="padding:6px 10px;font-size:.8rem;color:#64748b">Qualification</td><td style="padding:6px 10px;font-size:.82rem">'+esc(qual)+'</td></tr>';

    if (!rows) return;
    card.style.display = '';
    card.innerHTML =
      '<div class="jp-card" style="margin-bottom:14px;">' +
        '<div class="jp-sec-head" style="background:linear-gradient(135deg,#1a56db,#1e40af);display:flex;align-items:center;gap:8px;">' +
          '<i class="fa-brands fa-google"></i> Set as Preferred Source on Google' +
        '</div>' +
        '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">'+rows+'</table></div>' +
      '</div>';
  }

  /* § 3 — QUICK HIGHLIGHTS UPDATER */
  function updateHighlights(job) {
    var hl = document.getElementById('hlList');
    if (!hl) return;
    var bd = job.basic_details || {};
    var dates = job.important_dates || {};
    var items = [];
    var org = bd.organization_name || bd.post_name || job.organization || '';
    if (org) items.push('Organisation: '+org.slice(0,60));
    var posts = bd.total_vacancies || bd.total_vacancy || job.total_vacancy || job.vacancies || '';
    if (posts) items.push('Total Posts: '+String(posts));
    var ld = dates.last_date_to_apply || dates.last_date || job.lastDate || job.last_date || '';
    if (ld) {
      var dm = ld.match(/^(\d{4})-(\d{2})-(\d{2})/);
      if (dm) ld = dm[3]+'/'+dm[2]+'/'+dm[1];
      items.push('\u25b3 Last Date: '+ld);
    } else {
      items.push('\u25b3 Last Date: See Notification');
    }
    var mode = bd.application_mode || job.apply_mode || job.applyMode || '';
    if (mode) items.push('Apply Mode: '+mode);
    hl.innerHTML = items.map(function(t){
      return '<div class="jp-hl-item"><i class="fa-solid fa-circle-check"></i><span>'+esc(t)+'</span></div>';
    }).join('');
  }

  /* § 4 — IMPORTANT DATES SIDEBAR */
  function updateDatesSidebar(job) {
    var dates = job.important_dates || {};
    var ld = dates.last_date_to_apply || dates.last_date || dates.application_end_date || job.lastDate || job.last_date || '';
    var todayEl = document.getElementById('dateToday');
    var lastRow = document.getElementById('dateLastRow');
    var lastVal = document.getElementById('dateLastVal');
    var now = new Date();
    if (todayEl) todayEl.textContent = now.getDate()+'/'+(now.getMonth()+1)+'/'+now.getFullYear();
    if (ld && lastRow && lastVal) {
      var dm = ld.match(/^(\d{4})-(\d{2})-(\d{2})/);
      if (dm) ld = dm[3]+'/'+dm[2]+'/'+dm[1];
      lastVal.textContent = ld;
      lastRow.style.display = '';
    }
  }

  /* § 5 — SEO TAGS */
  function updateSeo(job, slug) {
    var bd = job.basic_details || {};
    var title = job.title || bd.job_title || bd.post_name || '';
    if (!title || !slug) return;
    var canon = SITE+'/data/jobs/'+slug+'/';
    var cl = document.querySelector('link[rel="canonical"]');
    if (cl) cl.href = canon;
    setMeta('property','og:url', canon);
    setMeta('property','og:title', title+' | Top Sarkari Jobs');
    setMeta('name','robots','index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1');
  }
  function setMeta(a,v,c){
    var el=document.querySelector('meta['+a+'="'+v+'"]');
    if(!el){el=document.createElement('meta');el.setAttribute(a,v);document.head.appendChild(el);}
    el.content=c;
  }

  /* § 6 — LINK REWRITER */
  function rewriteLinks() {
    document.querySelectorAll('a[href]').forEach(function(a){
      var h = a.getAttribute('href')||'';
      var sm = h.match(/[?&]slug=([^&]+)/);
      if (sm){ a.href='/data/jobs/'+sm[1]+'/'; return; }
      var om = h.match(/^\/jobs\/([^\/]+)\/?$/);
      if (om) a.href='/data/jobs/'+om[1]+'/';
    });
  }

  /* § 7 — SLUG GETTER */
  function getSlug() {
    var m = location.pathname.match(/\/data\/jobs\/([^\/]+)/);
    if (m) return m[1];
    m = location.pathname.match(/\/jobs\/([^\/]+)/);
    if (m) return m[1];
    try{ return sessionStorage.getItem('__tsj_slug')||''; }catch(_){ return ''; }
  }

  /* § 8 — MAIN HANDLER */
  function onJobReady(job) {
    if (!job) return;
    var slug = getSlug() || job.slug || '';
    renderPreferredSourceCard(job);
    updateHighlights(job);
    updateDatesSidebar(job);
    if (slug) updateSeo(job, slug);
    rewriteLinks();
    // Remove duplicates after rendering completes
    setTimeout(removeDuplicateSections, 300);
    setTimeout(removeDuplicateSections, 800);
    setTimeout(removeDuplicateSections, 1500);
  }

  /* § 9 — INIT */
  function init() {
    rewriteLinks();

    // Already rendered
    if (window.__TSJ_RENDER_DONE && window.__TSJ_RAW_JOB) {
      setTimeout(function(){ onJobReady(window.__TSJ_RAW_JOB); }, 0);
      return;
    }

    // Chain into existing callback (don't overwrite — chain)
    var prev = window.__TSJ_ON_RENDER_DONE;
    window.__TSJ_ON_RENDER_DONE = function(job) {
      if (typeof prev === 'function') try{ prev(job); }catch(_){}
      setTimeout(function(){ onJobReady(job); }, 50);
    };

    // Fallback poll
    var p=0, pid=setInterval(function(){
      p++;
      if (window.__TSJ_RAW_JOB || p>100){ clearInterval(pid); onJobReady(window.__TSJ_RAW_JOB||null); }
    },150);
  }

  if (document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',init);
  } else { init(); }

  window.TSJ = window.TSJ||{};
  window.TSJ.removeDuplicates = removeDuplicateSections;
  window.TSJ.onJobReady = onJobReady;
})();
