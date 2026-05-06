  <script>
  (function () {
    'use strict';

    // ---- Search System with proper async data loading ----
    const ALL_LINKS = [];
    let dataLoaded = false;
    let pendingSearches = [];

    // Base static links (always available)
    const STATIC_LINKS = [
      { text: 'Latest Jobs 2026', href: 'view.html?section=latest%20jobs', icon: 'fa-bolt', tags: 'latest naukri vacancy new' },
      { text: 'Upcoming Jobs', href: 'view.html?section=upcoming-jobs', icon: 'fa-calendar-plus', tags: 'upcoming future new' },
      { text: 'India All Current Running Jobs', href: 'view.html?section=Latest%20Govt%20Jobs', icon: 'fa-globe', tags: 'all india govt central' },
      { text: 'Last Date Near Jobs', href: 'view.html?section=Jobs%20with%20Last%20date', icon: 'fa-clock', tags: 'last date deadline urgent' },
      { text: 'Top 20 Jobs 2026', href: 'view.html?section=Top%2020%20Jobs', icon: 'fa-medal', tags: 'top best popular trending' },
      { text: '8th Pass Jobs', href: 'view.html?section=8th%20Pass', icon: 'fa-school', tags: '8th eighth primary' },
      { text: '10th Pass Jobs', href: 'view.html?section=10th%20Pass%20jobs', icon: 'fa-certificate', tags: '10th tenth matric pass' },
      { text: '12th Pass Jobs', href: 'view.html?section=12th%20Pass%20jobs', icon: 'fa-file-certificate', tags: '12th twelfth intermediate pass' },
      { text: 'ITI Pass Jobs', href: 'view.html?section=ITI%20Pass%20jobs', icon: 'fa-tools', tags: 'iti trade technical' },
      { text: 'Diploma Jobs', href: 'view.html?section=Diploma%20Jobs', icon: 'fa-scroll', tags: 'diploma polytechnic technical' },
      { text: 'B.Tech Jobs', href: 'view.html?section=B.Tech%20Jobs', icon: 'fa-microchip', tags: 'btech mtech engineering graduate' },
      { text: 'B.A Pass Jobs', href: 'view.html?section=B.A%20Pass', icon: 'fa-user-graduate', tags: 'ba arts graduate pass' },
      { text: 'Graduation Jobs', href: 'view.html?section=Graduation%20jobs', icon: 'fa-university', tags: 'graduation graduate degree' },
      { text: 'Post Graduation Jobs', href: 'view.html?section=Post%20Graduation%20jobs', icon: 'fa-user-tie', tags: 'post graduation pg masters mba' },
      { text: 'Medical Jobs', href: 'view.html?section=Medical%2F%20Healthcare%20Jobs', icon: 'fa-stethoscope', tags: 'medical doctor nurse aiims health' },
      { text: 'Railway Jobs 2026', href: 'view.html?section=Railway%20Jobs', icon: 'fa-train', tags: 'railway rrb ntpc group d loco' },
      { text: 'Police Jobs 2026', href: 'view.html?section=Police%20Jobs', icon: 'fa-shield-halved', tags: 'police constable si sub inspector' },
      { text: 'Bank Jobs 2026', href: 'view.html?section=Bank%20Jobs', icon: 'fa-building-columns', tags: 'bank ibps sbi rbi po clerk' },
      { text: 'Teacher Jobs 2026', href: 'view.html?section=Teacher%20Jobs', icon: 'fa-chalkboard-user', tags: 'teacher tet ctet pgt tgt school' },
      { text: 'Army / Navy / Air Force', href: 'view.html?section=Indian%20ARMY%20jobs', icon: 'fa-star', tags: 'army navy air force defence military agniveer' },
      { text: 'Govt Scheme & Yojna', href: 'view.html?section=Govt%20Scheme%20Yojna', icon: 'fa-hand-holding-heart', tags: 'govt scheme yojana benefit pm' },
      { text: 'Haryana Jobs', href: 'view.html?section=Haryana%20All%20State%20Jobs', icon: 'fa-location-dot', tags: 'haryana hssc hpsc jobs state' },
      { text: 'Admit Cards 2026', href: 'category.html?group=admit-result', icon: 'fa-id-card', tags: 'admit card hall ticket download exam' },
      { text: 'Latest Results 2026', href: 'category.html?group=admissions', icon: 'fa-trophy', tags: 'result sarkari result declared' },
      { text: 'Free Tools', href: 'tools.html', icon: 'fa-screwdriver-wrench', tags: 'tools image pdf resize compress' },
      { text: 'Helpdesk & Support', href: 'helpdesk.html', icon: 'fa-headset', tags: 'help support contact helpdesk query' },
    ];

    // Initialize with static links
    STATIC_LINKS.forEach(link => ALL_LINKS.push(link));

    // Load data from JSON files
    async function loadSearchData() {
      const existingHrefs = new Set(ALL_LINKS.map(l => l.href));
      
      const addItem = (name, url, category = '') => {
        if (!name || !url) return;
        const href = url;
        if (existingHrefs.has(href)) return;
        existingHrefs.add(href);
        const tags = (name + ' ' + category).toLowerCase();
        ALL_LINKS.push({ 
          text: name.trim(), 
          href: href, 
          icon: 'fa-briefcase', 
          tags: tags 
        });
      };

      try {
        // Load dynamic-sections.json
        const dynRes = await fetch('dynamic-sections.json?t=' + Date.now()).catch(() => null);
        if (dynRes && dynRes.ok) {
          const dyn = await dynRes.json();
          if (Array.isArray(dyn.sections)) {
            dyn.sections.forEach(sec => {
              const sectionTitle = sec.title || '';
              (sec.items || []).forEach(item => {
                addItem(item.name || item.title, item.url || item.link, sectionTitle);
              });
            });
          }
        }

        // Load jobs.json
        const jobsRes = await fetch('jobs.json?t=' + Date.now()).catch(() => null);
        if (jobsRes && jobsRes.ok) {
          const jobs = await jobsRes.json();
          const jobArrays = ['top_jobs', 'left_jobs', 'right_jobs', 'jobs', 'latest_jobs'];
          jobArrays.forEach(key => {
            if (Array.isArray(jobs[key])) {
              jobs[key].forEach(item => addItem(item.name || item.title, item.url || item.link, 'Jobs'));
            }
          });
        }

        // Load header_links.json
        const headerRes = await fetch('header_links.json?t=' + Date.now()).catch(() => null);
        if (headerRes && headerRes.ok) {
          const header = await headerRes.json();
          if (Array.isArray(header.header_links)) {
            header.header_links.forEach(item => addItem(item.name, item.link || item.url, 'Quick Link'));
          }
        }

      } catch(e) {
        console.warn('Search data load error:', e);
      }

      dataLoaded = true;
      
      // Process any pending searches that happened while loading
      pendingSearches.forEach(q => {
        if (q && q.trim().length >= 2) {
          showSuggest(q);
        }
      });
      pendingSearches = [];
    }

    function scoreMatch(link, q) {
      const haystack = (link.text + ' ' + (link.tags || '')).toLowerCase();
      const query = q.toLowerCase().trim();
      if (!query) return 0;
      let score = 0;
      const queryWords = query.split(/\s+/);
      for (const word of queryWords) {
        if (haystack.includes(word)) {
          score += word.length >= 4 ? 10 : 6;
          // Extra boost if word appears at start of text
          if (link.text.toLowerCase().startsWith(word)) score += 5;
        }
      }
      if (link.text.toLowerCase().includes(query)) score += 5;
      return score;
    }

    function search(q) {
      if (!q || !q.trim()) return [];
      const results = ALL_LINKS.map(l => ({ ...l, score: scoreMatch(l, q) }))
        .filter(l => l.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 10);
      return results;
    }

    function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

    // Hero search elements
    const input = document.getElementById('heroSearch');
    const btn = document.getElementById('heroSearchBtn');
    const suggest = document.createElement('div');
    suggest.id = 'heroSearchSuggest';
    suggest.className = 'search-suggest-dropdown';
    suggest.style.cssText = 'position:absolute;top:calc(100% + 4px);left:0;right:0;background:#fff;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.15);z-index:500;max-height:300px;overflow-y:auto;display:none;';
    
    // Insert suggest after hero-search-box wrapper
    const heroSearchBox = document.querySelector('.hero-search-box');
    if (heroSearchBox && heroSearchBox.parentNode) {
      heroSearchBox.parentNode.style.position = 'relative';
      heroSearchBox.parentNode.appendChild(suggest);
    }

    function showSuggest(q) {
      if (!input) return;
      
      // If data not loaded yet, queue this search
      if (!dataLoaded) {
        pendingSearches.push(q);
        if (q.trim().length >= 2) {
          suggest.innerHTML = '<div class="suggest-no" style="padding:12px;text-align:center;color:#64748b;"><i class="fa-solid fa-spinner fa-spin"></i> Loading suggestions...</div>';
          suggest.style.display = 'block';
        } else {
          suggest.style.display = 'none';
        }
        return;
      }
      
      if (!q.trim() || q.length < 2) {
        suggest.style.display = 'none';
        return;
      }
      
      const results = search(q);
      
      if (results.length === 0) {
        suggest.innerHTML = '<div class="suggest-no" style="padding:12px;text-align:center;color:#64748b;">No results found. Try: SSC, Railway, Bank, 10th pass...</div>';
        suggest.style.display = 'block';
        return;
      }
      
      suggest.innerHTML = results.map((r, i) => `
        <a class="suggest-item" href="${esc(r.href)}" role="option" style="display:flex;align-items:center;gap:10px;padding:10px 14px;font-size:.84rem;font-weight:600;color:#0f172a;text-decoration:none;border-bottom:1px solid #f8fafc;transition:background .12s;">
          <i class="fa-solid ${esc(r.icon || 'fa-briefcase')}" style="color:#1a56db;width:18px;"></i>
          <span>${esc(r.text)}</span>
        </a>
      `).join('');
      suggest.style.display = 'block';
    }

    function redirectSearch(q) {
      if (!q.trim()) {
        input.focus();
        return;
      }
      window.location.href = 'view.html?section=' + encodeURIComponent(q.trim());
    }

    let searchTimeout;
    if (input) {
      input.addEventListener('input', function (e) {
        clearTimeout(searchTimeout);
        const val = e.target.value;
        searchTimeout = setTimeout(() => showSuggest(val), 250);
      });
      
      input.addEventListener('focus', function () {
        if (dataLoaded && this.value.length >= 2) {
          showSuggest(this.value);
        } else if (!dataLoaded && this.value.length >= 2) {
          suggest.innerHTML = '<div class="suggest-no" style="padding:12px;text-align:center;color:#64748b;"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</div>';
          suggest.style.display = 'block';
        }
      });
      
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          redirectSearch(this.value);
        }
        if (e.key === 'Escape') {
          suggest.style.display = 'none';
        }
      });
    }
    
    if (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        if (input) redirectSearch(input.value);
      });
    }
    
    // Close suggest when clicking outside
    document.addEventListener('click', function (e) {
      if (input && suggest && !input.contains(e.target) && !suggest.contains(e.target)) {
        suggest.style.display = 'none';
      }
    });
    
    // Also handle the section search on view.html if present
    const sectionInput = document.getElementById('sectionSearchInput');
    const sectionBtn = document.getElementById('sectionSearchBtn');
    const sectionResults = document.getElementById('sectionSearchResults');
    
    if (sectionInput && sectionResults) {
      let sectionTimeout;
      sectionInput.addEventListener('input', function (e) {
        clearTimeout(sectionTimeout);
        const val = e.target.value;
        sectionTimeout = setTimeout(() => {
          if (!dataLoaded) return;
          if (val.trim().length < 2) {
            sectionResults.style.display = 'none';
            return;
          }
          const results = search(val);
          if (results.length === 0) {
            sectionResults.innerHTML = '<div class="search-no-results">No matches found.</div>';
            sectionResults.style.display = 'block';
          } else {
            sectionResults.innerHTML = results.map(r => `
              <a class="search-result-item" href="${esc(r.href)}" style="display:block;padding:10px 14px;text-decoration:none;border-bottom:1px solid #f1f5f9;">
                <div class="result-name" style="font-size:.84rem;font-weight:700;color:#0369a1;">${esc(r.text)}</div>
                <div class="result-meta" style="font-size:.72rem;color:#64748b;margin-top:2px;">Click to open</div>
              </a>
            `).join('');
            sectionResults.style.display = 'block';
          }
        }, 250);
      });
      
      if (sectionBtn) {
        sectionBtn.addEventListener('click', () => {
          if (sectionInput.value.trim()) {
            window.location.href = 'view.html?section=' + encodeURIComponent(sectionInput.value.trim());
          }
        });
      }
    }

    // Load data immediately
    loadSearchData();

    // ---- FAQ Toggle ----
    document.querySelectorAll('.faq-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const panel = this.nextElementSibling;
        const open = this.getAttribute('aria-expanded') === 'true';
        this.setAttribute('aria-expanded', !open);
        if (panel) panel.hidden = open;
      });
    });

    // ---- Mobile Menu Toggle ----
    const menuBtn = document.getElementById('menuBtn');
    const closeBtn = document.getElementById('closeMenuBtn');
    const mobileMenu = document.getElementById('mobileMenu');
    const overlay = document.getElementById('menuOverlay');

    if (mobileMenu) mobileMenu.hidden = true;
    if (overlay) overlay.hidden = true;

    function openMenu() {
      if (!mobileMenu || !overlay || !menuBtn) return;
      mobileMenu.hidden = false;
      overlay.hidden = false;
      menuBtn.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    }
    
    function closeMenu() {
      if (!mobileMenu || !overlay || !menuBtn) return;
      mobileMenu.hidden = true;
      overlay.hidden = true;
      menuBtn.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    }

    if (menuBtn && !menuBtn.dataset.offcanvasInit) {
      menuBtn.dataset.offcanvasInit = "1";
      menuBtn.addEventListener('click', openMenu);
      if (closeBtn) closeBtn.addEventListener('click', closeMenu);
      if (overlay) overlay.addEventListener('click', closeMenu);
      if (mobileMenu) {
        mobileMenu.addEventListener('click', function(e) { 
          if (e.target.closest('a')) closeMenu(); 
        });
      }
    }

    // ---- Desktop nav dropdowns ----
    document.querySelectorAll('[data-dd]').forEach(function (dd) {
      const btn = dd.querySelector('.nav-dd-btn');
      const menu = dd.querySelector('.nav-dd-menu');
      if (btn && menu) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          const isOpen = menu.style.display === 'block';
          document.querySelectorAll('.nav-dd-menu').forEach(m => m.style.display = '');
          if (!isOpen) menu.style.display = 'block';
        });
      }
    });
    
    document.addEventListener('click', function () {
      document.querySelectorAll('.nav-dd-menu').forEach(m => m.style.display = '');
    });

    // Mobile search button
    const mobileSearchBtn = document.getElementById('mobileSearchBtn');
    if (mobileSearchBtn) {
      mobileSearchBtn.addEventListener('click', function () {
        const heroSection = document.getElementById('hero-search-section');
        if (heroSection) {
          heroSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
          setTimeout(() => input?.focus(), 400);
        }
      });
    }

  })();
  </script>
