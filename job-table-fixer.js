/**
 * TopSarkariJobs — Job Detail Page Table Fixer + FSCD Layout
 * Fixes:
 *  1. Removes "gb headline ... 60ccea..." placeholder text
 *  2. Merges scattered single-row info-tables into proper merged table
 *  3. Applies FSCD-style clean card layout with proper horizontal scroll
 *  4. Handles vacancy table with proper multi-column display
 */
(function () {
  'use strict';

  /* ── Inject CSS once ── */
  if (!document.getElementById('tsj-fixer-css')) {
    var style = document.createElement('style');
    style.id = 'tsj-fixer-css';
    style.textContent = `
      /* ── Hide garbage placeholder text ── */
      .table-note strong[style*="60ccea"],
      .table-note strong {
        /* checked via JS below */
      }

      /* ── Vacancy & Eligibility Section overhaul ── */
      #vacancy-eligibility .job-card-body,
      .job-card-body {
        padding: 0 !important;
      }

      /* ── Merged overview table ── */
      .tsj-overview-table {
        width: 100%;
        border-collapse: collapse;
        font-size: .84rem;
      }
      .tsj-overview-table tr {
        border-bottom: 1px solid #e9eef4;
      }
      .tsj-overview-table tr:last-child {
        border-bottom: none;
      }
      .tsj-overview-table th {
        width: 36%;
        max-width: 160px;
        background: #f8fafc;
        color: #374151;
        font-weight: 700;
        padding: 10px 14px;
        text-align: left;
        vertical-align: top;
        word-break: break-word;
      }
      .tsj-overview-table td {
        padding: 10px 14px;
        color: #1e293b;
        line-height: 1.65;
        vertical-align: top;
        word-break: break-word;
        overflow-wrap: break-word;
      }
      .tsj-overview-table tr.tsj-hl-lastdate th,
      .tsj-overview-table tr.tsj-hl-lastdate td {
        background: #fef2f2;
        color: #dc2626;
        font-weight: 700;
      }

      /* ── Multi-col vacancy table ── */
      .tsj-vac-wrap {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
      }
      .tsj-vac-table {
        width: 100%;
        border-collapse: collapse;
        font-size: .82rem;
        min-width: 360px;
      }
      .tsj-vac-table th {
        background: #1d4ed8;
        color: #fff;
        padding: 9px 12px;
        font-weight: 700;
        text-align: left;
        white-space: nowrap;
      }
      .tsj-vac-table td {
        padding: 9px 12px;
        border-bottom: 1px solid #e9eef4;
        color: #1e293b;
        vertical-align: top;
        word-break: break-word;
      }
      .tsj-vac-table tbody tr:last-child td {
        border-bottom: none;
        font-weight: 700;
        background: #f0f9ff;
      }
      .tsj-vac-table tbody tr:hover td {
        background: #f8faff;
      }

      /* ── Section sub-heading inside card ── */
      .tsj-section-sub {
        font-size: .82rem;
        font-weight: 700;
        color: #1d4ed8;
        background: #f0f7ff;
        border-top: 1px solid #dbeafe;
        border-bottom: 1px solid #dbeafe;
        padding: 7px 14px;
        margin: 0;
      }

      /* ── Scroll hint ── */
      .tsj-scroll-hint {
        font-size: .7rem;
        color: #94a3b8;
        text-align: right;
        padding: 4px 14px 6px;
      }

      /* ── Important links grid ── */
      .links-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 10px;
        padding: 14px;
      }
      .link-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 5px;
        padding: 12px 8px 10px;
        border-radius: 10px;
        text-decoration: none;
        font-weight: 700;
        font-size: .75rem;
        text-align: center;
        transition: all .18s;
        min-height: 72px;
        word-break: break-word;
      }
      .link-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.13); }
      .link-btn i { font-size: 1.15rem; margin-bottom: 2px; display: block; }
      .btn-green  { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
      .btn-blue   { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
      .btn-red    { background: #fff5f5; color: #dc2626; border: 1px solid #fecaca; }
      .btn-orange { background: #fff7ed; color: #ea580c; border: 1px solid #fed7aa; }
      .btn-grey   { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
      .btn-grey:hover { background: #dbeafe; }

      /* Info table (dates etc) */
      .info-table {
        width: 100%;
        border-collapse: collapse;
        font-size: .84rem;
      }
      .info-table td, .info-table th {
        padding: 9px 14px;
        border-bottom: 1px solid #e9eef4;
        vertical-align: top;
        word-break: break-word;
      }
      .info-table thead tr:first-child th {
        background: #f8fafc;
        font-weight: 700;
        color: #374151;
      }
      .info-table tr:last-child td,
      .info-table tr:last-child th {
        border-bottom: none;
      }
      /* Scrollable wrapper */
      .table-scroll {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        width: 100%;
      }
    `;
    document.head.appendChild(style);
  }

  function isGbHeadline(txt) {
    return /gb\s+headline/i.test(txt) && /[0-9a-f]{6,}/i.test(txt);
  }

  function safe(v) { return (v || '').toString().trim(); }

  /* ── Main fixer — runs on DOMContentLoaded ── */
  function fixPage() {

    /* 1. Remove "gb headline ... 60ccea..." garbage text */
    var tableNotes = document.querySelectorAll('.table-note');
    tableNotes.forEach(function (note) {
      var strong = note.querySelector('strong');
      if (strong && isGbHeadline(strong.textContent)) {
        note.remove();
      }
    });

    /* 2. Fix vacancy-eligibility section */
    var vacSection = document.getElementById('vacancy-eligibility');
    if (!vacSection) return;

    var body = vacSection.querySelector('.job-card-body');
    if (!body) return;

    /* ── Collect all tables in the section ── */
    var allScrollWraps = Array.from(body.querySelectorAll('.table-scroll'));

    /* ── Strategy: Group tables by their column count ──
       - 2-col single-row tables → merge into one overview table
       - 3+ col tables with tbody → show as multi-col vacancy table
       - Any remaining table-note headings → show as section sub-head
    ── */

    var overviewRows = [];     // [label, value] pairs from 2-col rows
    var vacancyTables = [];    // multi-col tables with actual data
    var subHeadings = [];      // table-note paragraphs between groups

    /* Collect all children in order */
    var children = Array.from(body.childNodes);
    var i = 0;

    /* Group items */
    var groups = []; // {type: 'overview'|'vacancy'|'sub', data: ...}
    var currentGroup = null;

    children.forEach(function (node) {
      if (node.nodeType === Node.TEXT_NODE) return;
      var el = node;

      /* Sub-heading note (non-gb-headline) */
      if (el.classList && el.classList.contains('table-note')) {
        var strong = el.querySelector('strong');
        var txt = strong ? safe(strong.textContent) : '';
        if (!txt || isGbHeadline(txt)) return; // skip garbage
        groups.push({ type: 'sub', text: txt });
        currentGroup = null;
        return;
      }

      /* Table scroll wrapper */
      if (el.classList && el.classList.contains('table-scroll')) {
        var tbl = el.querySelector('table');
        if (!tbl) return;

        var heads = tbl.querySelectorAll('thead tr');
        var rows = tbl.querySelectorAll('tbody tr');

        /* Multi-col table with real data (3+ cols in thead or has tbody with rows) */
        var headCols = heads.length ? heads[0].querySelectorAll('th,td').length : 0;

        /* Check if this is a real vacancy/data table */
        var isMultiCol = (headCols >= 3) && (rows.length > 0 || (heads.length > 0 && tbl.querySelectorAll('tbody').length > 0));
        var hasBody = rows.length > 0;

        if (isMultiCol && hasBody) {
          /* Real multi-column table — keep as vacancy table */
          if (currentGroup && currentGroup.type === 'vacancy') {
            /* skip duplicates by checking if same thead */
          } else {
            groups.push({ type: 'vacancy', el: el });
            currentGroup = { type: 'vacancy' };
          }
          return;
        }

        /* 2-col single-row overview table */
        if (headCols === 2) {
          var th = heads[0].querySelectorAll('th,td');
          if (th.length === 2) {
            var label = safe(th[0].textContent);
            var value = safe(th[1].innerHTML); /* keep HTML for links */
            /* Skip if label looks like a full data dump (very long) */
            if (label.length > 80) {
              /* This is the malformed merged row — extract meaningful part */
              groups.push({ type: 'skip' });
              return;
            }
            /* Clean label: remove trailing colon */
            label = label.replace(/:+$/, '').trim();
            if (currentGroup && currentGroup.type === 'overview') {
              currentGroup.rows.push([label, value]);
            } else {
              currentGroup = { type: 'overview', rows: [[label, value]] };
              groups.push(currentGroup);
            }
            return;
          }
        }

        /* 3-col table with ONLY thead (no tbody) — like header row of vacancy table */
        if (headCols >= 3 && !hasBody) {
          /* This is a partial/malformed split of multi-col table — skip it */
          groups.push({ type: 'skip' });
          return;
        }

        /* Single-col or 1-col header — just a note, skip */
        if (headCols === 1) {
          groups.push({ type: 'skip' });
          return;
        }

        /* Fallback: keep original */
        if (currentGroup && currentGroup.type !== 'overview') {
          currentGroup = null;
        }
        groups.push({ type: 'raw', el: el });
        currentGroup = null;
      }
    });

    /* ── Now render cleaned content ── */
    body.innerHTML = '';

    /* Dedup: track seen overview labels */
    var seenLabels = new Set();
    /* Important overview labels to highlight */
    var importantLabels = new Set(['last date', 'last date to apply', 'closing date', 'last date of application']);

    groups.forEach(function (grp) {
      if (grp.type === 'skip') return;

      if (grp.type === 'sub') {
        var h = document.createElement('p');
        h.className = 'tsj-section-sub';
        h.textContent = grp.text;
        body.appendChild(h);
        return;
      }

      if (grp.type === 'overview' && grp.rows.length) {
        var table = document.createElement('table');
        table.className = 'tsj-overview-table';
        var tbody = document.createElement('tbody');
        grp.rows.forEach(function (pair) {
          var label = pair[0], val = pair[1];
          var key = label.toLowerCase();
          /* Skip duplicates */
          if (seenLabels.has(key)) return;
          /* Skip empty rows */
          if (!label && !val) return;
          /* Skip rows where label is very long (bad data) */
          if (label.length > 60) return;
          seenLabels.add(key);

          var tr = document.createElement('tr');
          var isLastDate = importantLabels.has(key);
          if (isLastDate) tr.className = 'tsj-hl-lastdate';

          var th = document.createElement('th');
          th.textContent = label;
          var td = document.createElement('td');
          td.innerHTML = val;
          tr.appendChild(th);
          tr.appendChild(td);
          tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        if (tbody.children.length) body.appendChild(table);
        return;
      }

      if (grp.type === 'vacancy') {
        var wrap = document.createElement('div');
        wrap.className = 'tsj-vac-wrap';
        var origTable = grp.el.querySelector('table');
        if (origTable) {
          /* Clone and restyle as vacancy table */
          var newTable = origTable.cloneNode(true);
          newTable.className = 'tsj-vac-table';
          newTable.style.width = '100%';
          newTable.style.minWidth = '';
          wrap.appendChild(newTable);
          body.appendChild(wrap);
          /* Scroll hint */
          var hint = document.createElement('div');
          hint.className = 'tsj-scroll-hint';
          hint.innerHTML = '<i class="fa-solid fa-left-right" style="font-size:.65rem;"></i> Scroll sideways to see all columns →';
          body.appendChild(hint);
        }
        return;
      }

      if (grp.type === 'raw') {
        body.appendChild(grp.el.cloneNode(true));
        return;
      }
    });
  }

  /* Run when DOM is ready */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fixPage);
  } else {
    fixPage();
  }

})();

/* ── 2. Auto-color Important Links buttons by label ── */
(function fixLinkButtons() {
  function applyColor(anchor) {
    var txt = (anchor.textContent || '').toLowerCase().trim();
    // Remove existing btn-grey class
    anchor.classList.remove('btn-grey');

    if (/apply\s*online|apply\s*now|apply\s*here|register/i.test(txt)) {
      anchor.classList.add('btn-green');
      // Change icon
      var icon = anchor.querySelector('i');
      if (icon) { icon.className = 'fa-solid fa-pen-to-square'; }
    } else if (/notification|download|pdf/i.test(txt)) {
      anchor.classList.add('btn-blue');
      var icon = anchor.querySelector('i');
      if (icon) { icon.className = 'fa-solid fa-file-pdf'; }
    } else if (/official\s*website|official\s*portal|visit/i.test(txt)) {
      anchor.classList.add('btn-red');
      var icon = anchor.querySelector('i');
      if (icon) { icon.className = 'fa-solid fa-globe'; }
    } else if (/admit\s*card|hall\s*ticket/i.test(txt)) {
      anchor.classList.add('btn-orange');
      var icon = anchor.querySelector('i');
      if (icon) { icon.className = 'fa-solid fa-id-card'; }
    } else if (/result|merit/i.test(txt)) {
      anchor.classList.add('btn-orange');
      var icon = anchor.querySelector('i');
      if (icon) { icon.className = 'fa-solid fa-trophy'; }
    } else {
      anchor.classList.add('btn-blue');
    }
  }

  function colorLinks() {
    var btns = document.querySelectorAll('.links-grid .link-btn.btn-grey');
    btns.forEach(applyColor);
    // Also fix icon spacing — wrap text in span if not already
    document.querySelectorAll('.links-grid .link-btn').forEach(function(btn) {
      btn.style.flexDirection = 'column';
      btn.style.alignItems = 'center';
      btn.style.gap = '6px';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', colorLinks);
  } else {
    colorLinks();
  }
})();
