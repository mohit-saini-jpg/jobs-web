/*
 * Core JavaScript for the rebuilt Top Sarkari Jobs website.
 *
 * This script handles fetching job and section data, rendering the
 * homepage and category pages, building a search index, and wiring
 * up interactive components like the mobile side menu and live
 * search.  It is designed to work with the new responsive HTML
 * structure and CSS styles defined in styles.css.  All functions
 * are written in vanilla JavaScript to keep the site lightweight
 * and fast on mobile devices.
 */

document.addEventListener('DOMContentLoaded', async () => {
  // Determine which page we are on via the data-page attribute on the body
  const pageType = document.body.getAttribute('data-page') || 'home';

  // Attempt to load data files in parallel.  If any fail, fallback
  // gracefully to empty objects so the page still functions.
  const [jobsData, dynamicData, headerData] = await Promise.all([
    fetchJSON('jobs.json'),
    fetchJSON('dynamic-sections.json'),
    fetchJSON('header_links.json')
  ]);

  // Build a unified search index from jobs and dynamic sections for
  // use on all pages.  The search index is an array of objects
  // describing each searchable item with its name, URL and group.
  const searchIndex = buildSearchIndex(jobsData, dynamicData);

  // Populate the footer social links if available
  loadFooterSocialLinks(headerData);

  // Initialise the mobile side menu controls
  setupSideMenu();

  // Initialise the live search component
  setupSearch(searchIndex);

  // Render page‑specific content
  if (pageType === 'home') {
    renderHomeCards(headerData);
    renderJobsSections(jobsData);
    renderDynamicSections(dynamicData);
  } else if (pageType === 'category') {
    // Determine which group to display based on the URL query
    const params = new URLSearchParams(window.location.search);
    const groupSlug = params.get('group');
    renderCategoryPage(groupSlug, jobsData, dynamicData);
  }
});

/**
 * Fetch a JSON file relative to the site root.  Returns an empty
 * object if the fetch fails for any reason, such as a missing file
 * or network error.  Errors are logged to the console for debugging.
 *
 * @param {string} url Path to the JSON file
 * @returns {Promise<Object>}
 */
async function fetchJSON(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Network response for ${url} was not ok`);
    return await response.json();
  } catch (err) {
    console.warn(`Failed to fetch ${url}:`, err);
    return {};
  }
}

/**
 * Build a flat search index from the jobs data and dynamic sections.
 * Each entry in the index includes the name, URL, whether it is
 * external, the originating group or section, and its type
 * ('job' or 'dynamic').  This index is used by the live search
 * component to filter and display results.
 *
 * @param {Object} jobsData Parsed jobs.json
 * @param {Object} dynamicData Parsed dynamic-sections.json
 * @returns {Array<Object>}
 */
function buildSearchIndex(jobsData, dynamicData) {
  const index = [];

  // Helper to process a jobs array (top_jobs, left_jobs, right_jobs)
  function processJobsArray(arr, defaultGroup) {
    if (!Array.isArray(arr)) return;
    let currentGroup = defaultGroup;
    for (const entry of arr) {
      if (entry.title) {
        // Use the title of a section as the group name for subsequent entries
        currentGroup = entry.title;
      } else if (entry.name) {
        index.push({
          name: entry.name,
          url: entry.url,
          external: entry.external,
          group: currentGroup,
          type: 'job'
        });
      }
    }
  }

  processJobsArray(jobsData.top_jobs, 'Top');
  processJobsArray(jobsData.left_jobs, 'Left');
  processJobsArray(jobsData.right_jobs, 'Right');

  // Include items from the dynamic sections
  if (dynamicData && Array.isArray(dynamicData.sections)) {
    dynamicData.sections.forEach(section => {
      if (section && Array.isArray(section.items)) {
        section.items.forEach(item => {
          index.push({
            name: item.name,
            url: item.url,
            external: item.external,
            group: section.title,
            type: 'dynamic',
            badge: item.badge
          });
        });
      }
    });
  }
  return index;
}

/**
 * Render the social media links in the footer.  Expects an array
 * called social_links on the headerData object.  Each link should
 * define a URL, name, colour and Font Awesome icon class.  Cards
 * are appended to the element with id 'footer-social'.
 *
 * @param {Object} headerData Parsed header_links.json
 */
function loadFooterSocialLinks(headerData) {
  const container = document.getElementById('footer-social');
  if (!container) return;
  const links = (headerData && headerData.social_links) || [];
  links.forEach(link => {
    const a = document.createElement('a');
    a.href = link.url || '#';
    a.target = '_blank';
    // Use the colour from the JSON if provided, otherwise fallback to primary colour
    a.style.backgroundColor = link.color || '#3b82f6';
    a.innerHTML = `<i class="${link.icon || ''}" style="margin-right:0.5rem"></i>${link.name}`;
    container.appendChild(a);
  });
}

/**
 * Initialise the mobile side menu.  Handles opening and closing
 * the menu, managing the overlay and updating ARIA attributes.
 */
function setupSideMenu() {
  const hamburger = document.getElementById('hamburger');
  const sideMenu = document.getElementById('side-menu');
  const overlay = document.getElementById('overlay');
  const closeBtn = document.getElementById('close-menu');
  if (!hamburger || !sideMenu || !overlay || !closeBtn) return;

  function openMenu() {
    sideMenu.classList.add('open');
    overlay.classList.add('show');
    hamburger.setAttribute('aria-expanded', 'true');
    sideMenu.setAttribute('aria-hidden', 'false');
  }

  function closeMenu() {
    sideMenu.classList.remove('open');
    overlay.classList.remove('show');
    hamburger.setAttribute('aria-expanded', 'false');
    sideMenu.setAttribute('aria-hidden', 'true');
  }

  hamburger.addEventListener('click', openMenu);
  closeBtn.addEventListener('click', closeMenu);
  overlay.addEventListener('click', closeMenu);

  // Close the menu when pressing the Escape key
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && sideMenu.classList.contains('open')) {
      closeMenu();
    }
  });
}

/**
 * Initialise the live search.  As the user types into the search
 * input, filter the search index and display a list of matching
 * results.  Clicking a result will navigate to the item and hide
 * the results list.  The search results container is hidden when
 * clicking outside the input or results.
 *
 * @param {Array<Object>} searchIndex Prebuilt search index
 */
function setupSearch(searchIndex) {
  const input = document.getElementById('search-input');
  const resultsDiv = document.getElementById('search-results');
  if (!input || !resultsDiv) return;

  input.addEventListener('input', () => {
    const query = input.value.trim().toLowerCase();
    if (!query) {
      resultsDiv.innerHTML = '';
      resultsDiv.classList.remove('show');
      return;
    }
    const results = searchIndex.filter(item => item.name.toLowerCase().includes(query)).slice(0, 15);
    const list = document.createElement('ul');
    if (results.length === 0) {
      const li = document.createElement('li');
      li.innerHTML = '<span style="padding:0.5rem;display:block;">No results found</span>';
      list.appendChild(li);
    } else {
      results.forEach(item => {
        const li = document.createElement('li');
        const a = document.createElement('a');
        // Escape the query for regex and highlight matches
        const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escaped})`, 'gi');
        a.innerHTML = item.name.replace(regex, '<mark>$1</mark>');
        a.href = '#';
        a.addEventListener('click', e => {
          e.preventDefault();
          openLink(item);
          // Hide results and clear input after selection
          resultsDiv.classList.remove('show');
          resultsDiv.innerHTML = '';
          input.value = '';
        });
        li.appendChild(a);
        list.appendChild(li);
      });
    }
    resultsDiv.innerHTML = '';
    resultsDiv.appendChild(list);
    resultsDiv.classList.add('show');
  });

  // Hide search results when clicking outside
  document.addEventListener('click', e => {
    if (!resultsDiv.contains(e.target) && e.target !== input) {
      resultsDiv.classList.remove('show');
    }
  });
}

/**
 * Render the quick access cards on the homepage.  These come from
 * the home_links array in header_links.json.  Each card uses
 * the .job-card class and optionally applies a background colour.
 *
 * @param {Object} headerData Parsed header_links.json
 */
function renderHomeCards(headerData) {
  const container = document.getElementById('home-cards');
  if (!container) return;
  const homeLinks = (headerData && headerData.home_links) || [];
  homeLinks.forEach(link => {
    const card = document.createElement('div');
    card.className = 'job-card';
    // Apply colour if provided
    if (link.color) {
      // Make sure text is readable on coloured backgrounds
      card.style.backgroundColor = link.color;
      card.style.color = '#ffffff';
    }
    card.innerHTML = `<span>${link.name}</span>`;
    card.addEventListener('click', () => openLink(link));
    container.appendChild(card);
  });
}

/**
 * Render the job sections (top, left and right) on the homepage.  Each
 * section is displayed in its respective container.  Section titles
 * are inserted as headers with a coloured background taken from
 * the JSON data.  Job entries appear as clickable cards.
 *
 * @param {Object} jobsData Parsed jobs.json
 */
function renderJobsSections(jobsData) {
  const topContainer = document.getElementById('top-jobs');
  const leftContainer = document.getElementById('left-jobs');
  const rightContainer = document.getElementById('right-jobs');
  if (!topContainer || !leftContainer || !rightContainer) return;

  function renderSection(arr, container) {
    if (!Array.isArray(arr)) return;
    let currentColor = null;
    for (let i = 0; i < arr.length; i++) {
      const entry = arr[i];
      if (entry.title) {
        // Create a header for the section
        currentColor = entry.color || null;
        const header = document.createElement('div');
        header.className = 'section-header';
        header.style.backgroundColor = currentColor || '#3b82f6';
        header.textContent = entry.title;
        container.appendChild(header);
      } else if (entry.name) {
        // Render a job card
        const card = document.createElement('div');
        card.className = 'job-card';
        if (currentColor) {
          // Lighten the colour for the card background and use the base
          // colour for the left border
          card.style.backgroundColor = lightenColor(currentColor, 0.85);
          card.style.borderLeft = `4px solid ${currentColor}`;
        }
        card.innerHTML = `<span>${entry.name}</span>`;
        card.addEventListener('click', () => openLink(entry));
        container.appendChild(card);
      }
    }
  }

  renderSection(jobsData.top_jobs, topContainer);
  renderSection(jobsData.left_jobs, leftContainer);
  renderSection(jobsData.right_jobs, rightContainer);
}

/**
 * Render the dynamic sections such as Latest Jobs, Upcoming Jobs, etc.
 * Each section is displayed in a box containing a coloured header,
 * a list of items and a View More link.  All boxes are appended to
 * the element with id 'dynamic-sections'.
 *
 * @param {Object} dynamicData Parsed dynamic-sections.json
 */
function renderDynamicSections(dynamicData) {
  const container = document.getElementById('dynamic-sections');
  if (!container || !dynamicData || !Array.isArray(dynamicData.sections)) return;
  dynamicData.sections.forEach(section => {
    const box = document.createElement('div');
    box.className = 'section-box';
    // Header
    const header = document.createElement('div');
    header.className = 'section-header';
    const colour = section.color || '#3b82f6';
    header.style.backgroundColor = colour;
    header.innerHTML = `<i class="${section.icon || 'fas fa-briefcase'}" style="margin-right:0.5rem"></i>${section.title}`;
    box.appendChild(header);
    // Items list
    const itemsDiv = document.createElement('div');
    itemsDiv.className = 'section-items';
    const items = Array.isArray(section.items) ? section.items.slice(0, 10) : [];
    items.forEach(item => {
      const itemDiv = document.createElement('div');
      itemDiv.className = 'section-item';
      itemDiv.style.borderLeftColor = colour;
      itemDiv.innerHTML = `<span>${item.name}</span>`;
      itemDiv.addEventListener('click', () => openLink(item));
      itemsDiv.appendChild(itemDiv);
    });
    box.appendChild(itemsDiv);
    // View more link
    const moreDiv = document.createElement('div');
    moreDiv.className = 'view-more';
    const moreLink = document.createElement('a');
    moreLink.textContent = 'View More';
    if (section.viewMoreType === 'external' && section.viewMoreUrl) {
      moreLink.href = section.viewMoreUrl;
      moreLink.target = '_blank';
    } else if (section.viewMoreType === 'internal' && section.viewMoreUrl) {
      moreLink.href = `view.html?url=${encodeURIComponent(section.viewMoreUrl)}&name=${encodeURIComponent(section.title)}`;
    } else {
      // Default: no action
      moreLink.href = '#';
    }
    moreDiv.appendChild(moreLink);
    box.appendChild(moreDiv);
    container.appendChild(box);
  });
}

/**
 * Render a category page based on the slug from the URL.  Looks up
 * the appropriate section from jobsData or dynamicData to pull the
 * list of items to display.  Provides descriptive text for the
 * category and falls back gracefully if the slug is unknown.
 *
 * @param {string|null} groupSlug Slug extracted from the query string
 * @param {Object} jobsData Parsed jobs.json
 * @param {Object} dynamicData Parsed dynamic-sections.json
 */
function renderCategoryPage(groupSlug, jobsData, dynamicData) {
  const titleEl = document.getElementById('category-title');
  const descEl = document.getElementById('category-description');
  const grid = document.getElementById('category-grid');
  if (!titleEl || !descEl || !grid) return;

  // Mapping of slugs to their titles, source and descriptions
  const groups = {
    study: {
      title: 'Study‑wise Jobs',
      from: 'top',
      sectionTitle: 'Study wise Jobs',
      description: 'Explore government job opportunities categorised by education level. Whether you passed class 8, 10, 12 or hold a diploma, find jobs tailored to your qualification.'
    },
    popular: {
      title: 'Popular Jobs',
      from: 'top',
      sectionTitle: '⭐ Popular Jobs Categories',
      description: 'Discover the most sought‑after government job categories in India. Browse by industry, role and trending career paths.'
    },
    state: {
      title: 'State‑wise Jobs',
      from: 'left',
      sectionTitle: 'State wise Jobs',
      description: 'Find government job openings across Indian states. Choose your state to view vacancies and notifications.'
    },
    admissions: {
      title: 'Admissions',
      from: 'left',
      sectionTitle: 'Admission',
      description: 'Stay updated on admission forms for universities, colleges and institutes. Find details about eligibility, application dates and entrance exams.'
    },
    admitresult: {
      title: 'Admit Card / Result / Answer Key / Syllabus',
      from: 'left',
      sectionTitle: 'Admit Card / Result / Answer Key / Syllabus',
      description: 'Access admit cards, exam results, answer keys and syllabuses for various recruitment exams. Stay prepared and informed.'
    },
    scheme: {
      title: 'Govt Scheme & Yojna',
      from: 'right',
      sectionTitle: 'Govt Scheme & Yojna',
      description: 'Learn about government schemes and yojanas offering benefits and subsidies. Browse information and eligibility criteria.'
    }
    // Additional slugs for dynamic sections can be defined here if needed
  };

  const config = groups[groupSlug];
  if (!config) {
    titleEl.textContent = 'Category Not Found';
    descEl.textContent = '';
    grid.innerHTML = '<p style="padding:1rem">The requested category does not exist.</p>';
    return;
  }

  titleEl.textContent = config.title;
  descEl.textContent = config.description;
  grid.innerHTML = '';

  // Extract the list of items for the selected group
  let items = [];
  if (config.from === 'top') {
    items = extractSectionItems(jobsData.top_jobs, config.sectionTitle);
  } else if (config.from === 'left') {
    items = extractSectionItems(jobsData.left_jobs, config.sectionTitle);
  } else if (config.from === 'right') {
    items = extractSectionItems(jobsData.right_jobs, config.sectionTitle);
  } else if (config.from === 'dynamic') {
    items = extractDynamicItems(dynamicData.sections, config.sectionTitle);
  }

  // Create cards for each item
  items.forEach(item => {
    const card = document.createElement('div');
    card.className = 'job-card';
    card.innerHTML = `<span>${item.name}</span>`;
    card.addEventListener('click', () => openLink(item));
    grid.appendChild(card);
  });
}

/**
 * Extract all entries from a jobs array that belong to a given section
 * title.  The function scans for the section header and collects
 * subsequent items until the next header or end of the array.
 *
 * @param {Array<Object>} arr Jobs array from jobs.json
 * @param {string} title Title of the section to extract
 * @returns {Array<Object>}
 */
function extractSectionItems(arr, title) {
  const result = [];
  if (!Array.isArray(arr)) return result;
  let collecting = false;
  for (let i = 0; i < arr.length; i++) {
    const entry = arr[i];
    if (entry.title && entry.title === title) {
      collecting = true;
      continue;
    }
    if (entry.title && collecting) {
      break;
    }
    if (collecting && entry.name) {
      result.push(entry);
    }
  }
  return result;
}

/**
 * Extract items from the dynamic sections by matching the section
 * title.  Returns the items array or an empty array if no section
 * matches.
 *
 * @param {Array<Object>} sections Dynamic sections array
 * @param {string} title Title of the dynamic section
 * @returns {Array<Object>}
 */
function extractDynamicItems(sections, title) {
  if (!Array.isArray(sections)) return [];
  const section = sections.find(sec => sec.title === title);
  return section && Array.isArray(section.items) ? section.items : [];
}

/**
 * Navigate to the URL associated with a job or dynamic item.  If
 * external is true, the link opens in a new tab.  Otherwise, the
 * user is taken to view.html with the URL and name encoded in the
 * query parameters.
 *
 * @param {Object} link Item containing at least name and url
 */
function openLink(link) {
  if (!link || !link.url) return;
  if (link.external) {
    window.open(link.url, '_blank');
  } else {
    const params = new URLSearchParams();
    params.set('url', encodeURIComponent(link.url));
    params.set('name', encodeURIComponent(link.name));
    window.location.href = `view.html?${params.toString()}`;
  }
}

/**
 * Compute a lighter variant of a hex colour by blending it towards
 * white.  The ratio defines how far to lighten the colour (0–1).
 *
 * @param {string} hex Hex code of the base colour (e.g. "#2563eb")
 * @param {number} ratio Number between 0 and 1 indicating the
 *        degree of lightening (0 = no change, 1 = white)
 * @returns {string} RGB string suitable for CSS
 */
function lightenColor(hex, ratio) {
  // Ensure we have a valid hex string
  if (typeof hex !== 'string' || !hex.startsWith('#')) return hex;
  let clean = hex.replace('#', '');
  if (clean.length === 3) {
    clean = clean.split('').map(ch => ch + ch).join('');
  }
  const r = parseInt(clean.substring(0, 2), 16);
  const g = parseInt(clean.substring(2, 4), 16);
  const b = parseInt(clean.substring(4, 6), 16);
  const newR = Math.round(r + (255 - r) * ratio);
  const newG = Math.round(g + (255 - g) * ratio);
  const newB = Math.round(b + (255 - b) * ratio);
  return `rgb(${newR}, ${newG}, ${newB})`;
}
