## 🚀 QUICK FIX — 2 MINUTES

### Problem
Age Limit Details table shows each character on separate row instead of proper layout.

### Solution (Pick ONE)

---

## **OPTION A: CSS-Only (EASIEST - Do This First!)**

Add this to your `job.html` `<style>` section:

```css
/* Age Limit table fix */
#ageCard .jp-table {
  table-layout: auto !important;
  min-width: 300px;
}

#ageCard .jp-table th,
#ageCard .jp-table td {
  width: auto !important;
  min-width: 140px;
  word-break: normal !important;
  overflow-wrap: normal !important;
}

/* Optional: Also fix similar tables */
#datesDetailCard .jp-table,
#feeCard .jp-table {
  table-layout: auto !important;
  min-width: 300px;
}

#datesDetailCard .jp-table th,
#datesDetailCard .jp-table td,
#feeCard .jp-table th,
#feeCard .jp-table td {
  width: auto !important;
  min-width: 140px;
  word-break: normal !important;
  overflow-wrap: normal !important;
}
```

**That's it! No HTML changes needed.**

---

## **OPTION B: HTML + CSS (Better Organization)**

### Find this in job.html:
```html
<div class="jp-card" id="ageCard" style="display:none;">
  <div class="jp-sec-head" style="background:linear-gradient(135deg,#0f766e,#0891b2);"><i class="fa-solid fa-user-clock"></i> Age Limit</div>
  <table class="jp-table"><tbody id="ageTableBody"></tbody></table>
</div>
```

### Replace with:
```html
<div class="jp-card" id="ageCard" style="display:none;">
  <div class="jp-sec-head" style="background:linear-gradient(135deg,#0f766e,#0891b2);"><i class="fa-solid fa-user-clock"></i> Age Limit</div>
  <div class="jp-table-wrap-fixed">
    <table class="jp-table"><tbody id="ageTableBody"></tbody></table>
  </div>
</div>
```

Then add this CSS:
```css
.jp-table-wrap-fixed {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.jp-table-wrap-fixed .jp-table {
  table-layout: auto !important;
  min-width: 300px;
}

.jp-table-wrap-fixed .jp-table th,
.jp-table-wrap-fixed .jp-table td {
  width: auto !important;
  min-width: 140px;
  word-break: normal !important;
  overflow-wrap: normal !important;
}
```

---

## **OPTION C: JavaScript (No HTML Changes)**

Add to end of `job.html` before `</body>`:

```html
<script>
(function() {
  function fixAgeTable() {
    const ageCard = document.getElementById('ageCard');
    if (ageCard) {
      const table = ageCard.querySelector('.jp-table');
      if (table) {
        table.style.tableLayout = 'auto';
        table.style.minWidth = '300px';
        
        table.querySelectorAll('th, td').forEach(cell => {
          cell.style.width = 'auto';
          cell.style.minWidth = '140px';
          cell.style.wordBreak = 'normal';
          cell.style.overflowWrap = 'normal';
        });
      }
    }
  }
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fixAgeTable);
  } else {
    fixAgeTable();
  }
})();
</script>
```

---

## Verify It Works

1. Open job page with Age Limit details
2. Check that Age Limit table looks like:
   ```
   ┌──────────────────┬─────────────────┐
   │ Minimum Age      │ 18 years        │
   │ Maximum Age      │ 40 years        │
   │ Age Relaxation   │ SC/ST: 5 years  │
   └──────────────────┴─────────────────┘
   ```
   ✅ NOT like individual characters per row

3. Test on mobile phone
4. Check other tables still work (Vacancy Details, etc.)

---

## Summary

| What | How Long | Difficulty |
|------|----------|-----------|
| CSS-Only Fix | 2 min | Easy |
| HTML + CSS | 5 min | Medium |
| JavaScript | 3 min | Medium |

**Start with CSS-Only** — it's quickest and safest.

---

## Files Provided

- 📄 **AGE_LIMIT_TABLE_FIX_GUIDE.md** → Complete guide (read this for details)
- 🎨 **age-limit-table-fix.css** → Full CSS file
- 📝 **AGE_LIMIT_TABLE_FIX.html** → HTML patch with CSS
- 🔧 **age-limit-table-fix.js** → JavaScript fix
- 🔬 **TECHNICAL_EXPLANATION.md** → Deep dive into why this happens

Pick what you need and apply!

---

**Last Updated:** 2026-05-21
