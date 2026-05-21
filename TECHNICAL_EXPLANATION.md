# Technical Deep Dive: Age Limit Table CSS Issue

## Problem Analysis

### Current CSS (Problematic)
```css
.jp-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;  /* ← PROBLEM 1: Forces fixed column widths */
  min-width: 320px;
}

.jp-table th {
  width: 35%;  /* ← PROBLEM 2: Only 35% width for header */
  background: #f8fafc;
  color: #374151;
  font-size: 0.82rem;
  font-weight: 700;
  padding: 10px 14px;
  text-align: left;
  vertical-align: top;
  word-break: break-word;  /* ← PROBLEM 3: Breaks at every character */
  overflow-wrap: break-word;
}

.jp-table td {
  color: #1e293b;
  font-size: 0.84rem;
  padding: 10px 14px;
  vertical-align: top;
  line-height: 1.6;
  word-break: break-word;  /* ← PROBLEM 3: Same here */
  overflow-wrap: break-word;
}
```

### How The Browser Renders It

```
Step 1: Browser parses .jp-table { table-layout: fixed; }
        ↓
Step 2: Allocates column widths: 35% (th) + 65% (td)
        ↓
Step 3: For 2-column table on 600px wide screen:
        th width = 600px × 35% = 210px
        td width = 600px × 65% = 390px
        ↓
Step 4: Tries to fit content "Minimum Age" (11 chars) in 210px
        With padding: 210px - 28px (padding) = 182px available
        ↓
Step 5: Font size 0.82rem ≈ 13px per character
        Content width needed: 11 × 13px ≈ 143px (fits!)
        ↓
Step 6: But for 2-column layout with long values:
        "18-25 years, 30-45 years (for Ex-servicemen)" (46 chars)
        ↓
Step 7: Tries to fit in 390px td
        With padding: 390px - 28px = 362px available
        ↓
Step 8: 46 chars × ~13px = 598px needed
        598px > 362px → DOESN'T FIT
        ↓
Step 9: Browser applies word-break: break-word
        Since there are no spaces in "18-25" etc, breaks at EVERY CHARACTER
        ↓
Step 10: Result: Each character on own line!
```

### The Cascade Problem

When multiple narrow constraints combine:
```
table-layout: fixed   →  Fixed column widths
    +
narrow th (35%)       →  Limited space for labels
    +
word-break:break-word →  Aggressive character-level breaking
    ↓
Each character wraps to next line
```

---

## Solution Analysis

### Why `table-layout: auto` Fixes It

```css
/* FIXED CSS */
#ageCard .jp-table {
  table-layout: auto !important;  /* ← KEY FIX */
  min-width: 300px;
}

#ageCard .jp-table th {
  width: auto !important;  /* ← Allow auto-sizing */
  min-width: 140px;        /* ← But keep minimum */
}

#ageCard .jp-table td {
  width: auto !important;
  min-width: 150px;
  word-break: normal !important;  /* ← Allow proper wrapping */
  overflow-wrap: normal !important;
}
```

### How This Renders Correctly

```
Step 1: Browser sees table-layout: auto
        ↓
Step 2: Measures content to determine column widths
        "Minimum Age" needs ~100px
        "18-25 years" needs ~80px
        ↓
Step 3: Adds min-width constraints:
        th: min 140px
        td: min 150px
        ↓
Step 4: Final column allocation:
        th: max(content, 140px) = 140px
        td: max(content, 150px) = 150px+
        ↓
Step 5: Browser applies word-break: normal
        Breaks only at space characters (normal word wrapping)
        ↓
Step 6: Result: Proper multi-line text!
        "Minimum Age" fits in one line
        Long values wrap at spaces
```

---

## CSS Property Reference

### `table-layout` Property

| Value | Behavior | Use Case |
|-------|----------|----------|
| `fixed` | Browser uses widths in CSS | Multi-column with predictable layout |
| `auto` | Browser measures content | Tables with variable content |

### When `fixed` Works
```
Example: 5-column vacancy table with consistent data
┌─────┬──────┬──────┬──────┬──────┐
│ Cat │ Gen  │ OBC  │ SC   │ ST   │
├─────┼──────┼──────┼──────┼──────┤
│ A   │  10  │  5   │  3   │  2   │
│ B   │   8  │  4   │  2   │  1   │
└─────┴──────┴──────┴──────┴──────┘

Each column width is predictable: 20% each
```

### When `fixed` Fails
```
Example: 2-column info table with variable lengths
┌────────────────────┬──────────────────────────┐
│ Minimum Age        │ 18-25 years (General)    │
│ Maximum Age        │ 35-42 years (ST: +5 yrs) │
│ Age Relaxation     │ SC/ST: 5 yrs, Ex-Svc: 3 │
└────────────────────┴──────────────────────────┘

Data length varies wildly → fixed layout breaks content
```

### `word-break` Property

| Value | Breaks At | Example |
|-------|-----------|---------|
| `normal` | Space only | "Long text" → "Long" / "text" |
| `break-word` | Any character | "Longtext" → "L" / "o" / "n" / ... |
| `break-all` | Force break | "Longtext" → "Long" / "tex" / "t" |

---

## Browser Rendering Flow

```
┌─────────────────────────────────────────┐
│ 1. Parse CSS Rules                      │
│    - table-layout: fixed                │
│    - word-break: break-word             │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 2. Build Table Box Model                │
│    - Allocate 35% for th, 65% for td   │
│    - Calculate pixel widths             │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 3. Layout Content into Cells            │
│    - Try to fit text in allocated space │
│    - Use word-break rule if overflows   │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ 4. Render                               │
│    - Draw borders, backgrounds, text    │
└─────────────────────────────────────────┘
```

---

## Test Cases

### Test 1: Age Limit Table
```html
<table class="jp-table">
  <tr>
    <th>Minimum Age</th>
    <td>18 years</td>
  </tr>
  <tr>
    <th>Maximum Age</th>
    <td>40 years</td>
  </tr>
  <tr>
    <th>Age Relaxation</th>
    <td>SC/ST: 5 years, Ex-Servicemen: 3 years</td>
  </tr>
</table>
```

**Expected (with fix):**
```
┌──────────────────┬──────────────────────────────┐
│ Minimum Age      │ 18 years                     │
│ Maximum Age      │ 40 years                     │
│ Age Relaxation   │ SC/ST: 5 years,              │
│                  │ Ex-Servicemen: 3 years       │
└──────────────────┴──────────────────────────────┘
```

### Test 2: Important Dates Table
```html
<table class="jp-table">
  <tr>
    <th>Application Start Date</th>
    <td>2026-05-21</td>
  </tr>
  <tr>
    <th>Last Date for Application</th>
    <td>2026-06-30</td>
  </tr>
</table>
```

**Expected:**
```
┌───────────────────────────────┬─────────────┐
│ Application Start Date        │ 2026-05-21  │
│ Last Date for Application     │ 2026-06-30  │
└───────────────────────────────┴─────────────┘
```

### Test 3: Vacancy Details Table (Should Remain Fixed)
```html
<table class="jp-vac-table">
  <thead>
    <tr>
      <th>Category</th>
      <th>Vacancies</th>
      <th>General</th>
      <th>OBC</th>
      <th>SC</th>
      <th>ST</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>A</td>
      <td>100</td>
      <td>50</td>
      <td>25</td>
      <td>15</td>
      <td>10</td>
    </tr>
  </tbody>
</table>
```

**Note:** This uses `.jp-vac-table` NOT `.jp-table`, so our fix doesn't affect it. ✓

---

## Specificity Analysis

```css
/* Original CSS (Specificity: 1 element selector) */
.jp-table {
  table-layout: fixed;  /* Specificity: 1 */
}

/* Our Fix (Specificity: 1 ID + 1 element + !important) */
#ageCard .jp-table {
  table-layout: auto !important;  /* Specificity: 101 + !important */
}
```

Why `!important`?
- Original rule: Specificity 1
- Our rule: Specificity 101 (1 ID + 1 element)
- Our rule already wins by specificity
- But using `!important` makes it impossible for inline styles to override

Specificity scores:
- Inline style: Specificity infinity (but we don't have any here)
- `!important`: Always wins (unless another `!important` with higher specificity)
- ID (#): 100 points
- Class (.): 10 points  
- Element: 1 point

---

## Browser Compatibility

| Browser | `table-layout:auto` | `word-break` | Status |
|---------|-------------------|--------------|--------|
| Chrome/Edge | ✅ Full support | ✅ Full support | Perfect |
| Firefox | ✅ Full support | ✅ Full support | Perfect |
| Safari | ✅ Full support | ⚠️ Partial (v6+) | Good |
| IE 11 | ✅ Full support | ✅ Full support | Works |
| IE 9-10 | ✅ Full support | ❌ Limited | Minimal |

**Graceful Degradation:**
If `word-break: normal` is not supported, browser defaults to `word-break: normal` anyway, so no visual difference.

---

## Performance Impact

```
Original CSS:
- Browser uses fixed layout algorithm (faster)
- Single pass through CSS
- No content measurement needed

Fixed CSS:
- Browser uses auto layout algorithm (slower)
- Measures content width
- Multiple passes may occur

Performance Difference:
- Negligible for modern browsers
- Age Limit table = 3 rows
- ~0.001ms slower (unmeasurable)
- No impact on page load time
```

---

## Recommended Application Order

1. **Immediate:** Apply CSS-only fix (Solution 1)
2. **Next Update:** Update HTML with wrapper (Solution 2)
3. **Optional:** Add JS for dynamic content (Solution 3)

This ensures:
- Quick fix without redeployment
- Proper markup on next release
- Future-proof for dynamic content

---

## Files Affected

When applying the fix to your codebase:

```
job.html (Primary)
├── job-renderer-patch.js (Applies styling)
├── script.js (May render tables dynamically)
└── styles (Contains CSS)

state-jobs.html (May have similar tables)
jobs-index.html (May have similar tables)
```

---

## References

- MDN: [`table-layout`](https://developer.mozilla.org/en-US/docs/Web/CSS/table-layout)
- MDN: [`word-break`](https://developer.mozilla.org/en-US/docs/Web/CSS/word-break)
- W3C: [CSS Table Module](https://www.w3.org/TR/CSS2/tables.html)

---

**Document Version:** 1.0  
**Created:** 2026-05-21  
**Last Modified:** 2026-05-21
