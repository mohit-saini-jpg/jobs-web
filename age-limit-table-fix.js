/**
 * AGE LIMIT TABLE FIX — JavaScript Patch
 * ════════════════════════════════════════════════════════════════
 * 
 * PROBLEM: Age Limit Details table shows each character on a new row
 *          due to table-layout:fixed + word-break:break-word issue
 * 
 * SOLUTION: This script fixes the CSS dynamically at runtime
 *          No HTML changes needed
 * 
 * HOW TO USE:
 * Add this ONE line to the end of your job.html <body> (before </body>):
 *   <script src="/age-limit-table-fix.js"></script>
 * 
 * OR embed the contents of this file directly before </body>
 * 
 * ════════════════════════════════════════════════════════════════
 */

(function() {
  'use strict';

  // Run once page is ready
  function fixAgeTable() {
    // Fix Age Limit table
    const ageCard = document.getElementById('ageCard');
    if (ageCard) {
      const table = ageCard.querySelector('.jp-table');
      if (table) {
        // Override the problematic CSS
        table.style.tableLayout = 'auto';
        table.style.minWidth = '300px';
        
        // Fix table cells
        const cells = table.querySelectorAll('th, td');
        cells.forEach(cell => {
          cell.style.width = 'auto';
          cell.style.minWidth = '140px';
          cell.style.wordBreak = 'normal';
          cell.style.overflowWrap = 'normal';
          cell.style.whiteSpace = 'normal';
        });
      }
    }

    // Also fix other similar info tables
    fixTableById('datesDetailCard');
    fixTableById('feeCard');
  }

  /**
   * Utility: Fix any table by card ID
   */
  function fixTableById(cardId) {
    const card = document.getElementById(cardId);
    if (!card) return;
    
    const table = card.querySelector('.jp-table');
    if (!table) return;
    
    table.style.tableLayout = 'auto';
    table.style.minWidth = '300px';
    
    const cells = table.querySelectorAll('th, td');
    cells.forEach(cell => {
      cell.style.width = 'auto';
      cell.style.minWidth = '140px';
      cell.style.wordBreak = 'normal';
      cell.style.overflowWrap = 'normal';
    });
  }

  // Run on DOMContentLoaded if document is still loading
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fixAgeTable);
  } else {
    // If document is already loaded, run immediately
    fixAgeTable();
  }

  // Also watch for dynamic content changes (MutationObserver)
  // In case tables are added/modified after page load
  const observer = new MutationObserver(function(mutations) {
    mutations.forEach(mutation => {
      // Check if Age Limit table was just added/modified
      if (mutation.addedNodes.length) {
        mutation.addedNodes.forEach(node => {
          if (node.id === 'ageCard' || node.id === 'datesDetailCard' || node.id === 'feeCard') {
            fixAgeTable();
          }
        });
      }
    });
  });

  // Start observing for changes
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: false,
  });

  // Export for manual use if needed
  window.fixAgeTable = fixAgeTable;
  window.fixTableById = fixTableById;
})();

/**
 * ALTERNATIVE: Inject CSS directly without JavaScript
 * 
 * If you prefer CSS-only solution, add this to your <style> block:
 * 
 * #ageCard .jp-table {
 *   table-layout: auto !important;
 *   min-width: 300px;
 * }
 * 
 * #ageCard .jp-table th,
 * #ageCard .jp-table td {
 *   width: auto !important;
 *   word-break: normal !important;
 *   overflow-wrap: normal !important;
 * }
 * 
 */
