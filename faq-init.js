/* faq-init.js — Universal FAQ accordion for all static detail pages
   Works on generate_website.py pages (styles-detail.css) where .faq-a is display:none
   Also works on generate_jobs.py static pages
   Attaches delegated click listener — no inline onclick needed
*/
(function() {
  'use strict';
  function initFAQ() {
    // Handle all .faq-item containers on the page
    document.querySelectorAll('.sec-card, .sec-body, .faq-sec-body, body').forEach(function(container) {
      // Use event delegation — one listener per container
      if (container._faqInitDone) return;
      container._faqInitDone = true;
      container.addEventListener('click', function(e) {
        var btn = e.target.closest('.faq-q');
        if (!btn) return;
        var item = btn.closest('.faq-item');
        if (!item) return;
        var ans = item.querySelector('.faq-a');
        if (!ans) return;
        var isOpen = btn.classList.contains('open');
        // Close all other FAQs in same card
        var parentCard = btn.closest('.sec-body') || btn.closest('.sec-card') || document;
        parentCard.querySelectorAll('.faq-q.open').forEach(function(openBtn) {
          if (openBtn === btn) return;
          openBtn.classList.remove('open');
          var openAns = openBtn.closest('.faq-item') && openBtn.closest('.faq-item').querySelector('.faq-a');
          if (openAns) { openAns.classList.remove('open'); openAns.style.display = 'none'; }
          // Rotate chevron back
          var chev = openBtn.querySelector('.fa-chevron-down, [class*="chevron"]');
          if (chev) chev.style.transform = '';
        });
        // Toggle current
        if (isOpen) {
          btn.classList.remove('open');
          ans.classList.remove('open');
          ans.style.display = 'none';
          var chev = btn.querySelector('.fa-chevron-down, [class*="chevron"]');
          if (chev) chev.style.transform = '';
        } else {
          btn.classList.add('open');
          ans.classList.add('open');
          ans.style.display = 'block';
          var chev = btn.querySelector('.fa-chevron-down, [class*="chevron"]');
          if (chev) chev.style.transform = 'rotate(180deg)';
        }
        e.stopPropagation();
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFAQ);
  } else {
    initFAQ();
  }
})();
