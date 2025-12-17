document.addEventListener("DOMContentLoaded", async () => {
  // Detect current page
  const currentPage = window.location.pathname.split("/").pop() || "index.html";

  // Load data from appropriate JSON file
  let data;
  const jsonFile =
    currentPage === "index.html" || currentPage === ""
      ? "jobs.json"
      : currentPage === "tools.html"
      ? "tools.json"
      : "services.json";
  try {
    const response = await fetch(jsonFile);
    data = await response.json();
  } catch (error) {
    console.error("Error loading data:", error);
    // Fallback empty data
    data = {
      image: [],
      pdf: [],
      video: [],
      services: [],
      top_jobs: [],
      left_jobs: [],
      right_jobs: [],
      news: [],
      scrolling_jobs: [],
      home_links: [],
    };
  }

  // Load header links (separate JSON)
  let headerData = null;
  try {
    const resp = await fetch("header_links.json");
    headerData = await resp.json();
  } catch (err) {
    console.warn("No header_links.json found or failed to load", err);
    headerData = { header_links: [], home_links: [] };
  }

  // Render header links (desktop + mobile)
  function loadHeaderLinks(headerData) {
    if (!headerData) return;
    const desktopContainer = document.getElementById("header-links");
    const mobileContainer = document.getElementById("header-links-mobile");

    const links = headerData.header_links || [];
    if (desktopContainer) {
      links.forEach((l) => {
        const a = document.createElement("a");
        a.href = l.link || l.url || "#";
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        const colorClass = l.color ? l.color : "bg-gray-800";
        a.className = `${colorClass} text-white px-4 py-2 rounded-lg font-semibold hover:opacity-90 transition duration-200 flex items-center`;
        a.innerHTML = `${l.name}`;
        desktopContainer.appendChild(a);
      });
    }

    if (mobileContainer) {
      links.forEach((l) => {
        const a = document.createElement("a");
        a.href = l.link || l.url || "#";
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.className = `px-4 py-2 rounded-lg bg-white text-blue-600 font-semibold hover:bg-blue-50 transition duration-200 block`;
        a.textContent = l.name;
        mobileContainer.appendChild(a);
      });
    }
  }

  // Get URL parameters
  const urlParams = new URLSearchParams(window.location.search);
  const jobParam = urlParams.get("job");
  const toolParam = urlParams.get("tool");

  // Page-specific elements
  const mainCategories = document.getElementById("main-categories");
  const subCategories = document.getElementById("sub-categories");
  const backButton = document.getElementById("back-button");
  const subCategoryTitle = document.getElementById("sub-category-title");
  const toolsCards = document.getElementById("tools-cards");
  const servicesCards = document.getElementById("services-cards");
  const toolIframe = document.getElementById("tool-iframe");
  const serviceModal = document.getElementById("service-modal");
  const modalServiceContent = document.getElementById("modal-service-content");
  const closeModalBtn = document.getElementById("close-modal");
  const loadingOverlay = document.getElementById("loading-overlay");
  const defaultState = document.getElementById("default-state");

  // Mobile menu elements
  const mobileMenuToggle = document.getElementById("mobile-menu-toggle");
  const mobileMenu = document.getElementById("mobile-menu");

  // Mobile menu toggle
  if (mobileMenuToggle && mobileMenu) {
    mobileMenuToggle.addEventListener("click", () => {
      mobileMenu.classList.toggle("hidden");
    });

    // Close mobile menu when clicking a link
    mobileMenu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        mobileMenu.classList.add("hidden");
      });
    });

    // Close mobile menu when clicking outside
    document.addEventListener("click", (e) => {
      if (
        !mobileMenu.contains(e.target) &&
        !mobileMenuToggle.contains(e.target)
      ) {
        mobileMenu.classList.add("hidden");
      }
    });
  }

  // Render header links (if any)
  loadHeaderLinks(headerData);

  // Load content based on current page
  if (currentPage === "index.html" || currentPage === "") {
    // Jobs page
    loadJobs();
    loadHomeLinks();
    loadFooterSocialLinks();
    loadWhatsAppChat();
  } else if (currentPage === "govt-services.html") {
    // Government services page
    loadGovernmentServices();

    // Close modal event listeners
    if (closeModalBtn) {
      closeModalBtn.addEventListener("click", () => {
        serviceModal.classList.add("hidden");
      });
    }

    // Close modal when clicking outside
    if (serviceModal) {
      serviceModal.addEventListener("click", (e) => {
        if (e.target === serviceModal) {
          serviceModal.classList.add("hidden");
        }
      });
    }
  } else if (currentPage === "tools.html") {
    // Tools page
    loadToolsSection();

    // Check if tool parameter is present and auto-load tool
    if (toolParam) {
      setTimeout(() => {
        autoLoadTool(toolParam);
      }, 500);
    }
  }

  // Category names mapping
  const categoryNames = {
    image: "Image Tools",
    pdf: "PDF Tools",
    video: "Video/Audio Tools",
  };

  // Category icons mapping
  const categoryIcons = {
    image: "fas fa-image text-green-500",
    pdf: "fas fa-file-pdf text-blue-500",
    video: "fas fa-video text-purple-500",
  };

  // Function to load tools section (only on tools.html)
  function loadToolsSection() {
    if (!mainCategories || !backButton) return;

    // Handle category button clicks
    document.querySelectorAll(".category-button").forEach((button) => {
      button.addEventListener("click", () => {
        const category = button.dataset.category;
        showSubCategories(category);
      });
    });

    // Handle back button
    backButton.addEventListener("click", () => {
      showMainCategories();
    });
  }

  // Function to auto-load a tool based on URL parameter
  function autoLoadTool(toolName) {
    // Search for the tool in all categories
    let foundTool = null;
    let foundCategory = null;

    for (const [category, tools] of Object.entries(data)) {
      if (
        category === "services" ||
        category === "top_jobs" ||
        category === "left_jobs" ||
        category === "right_jobs" ||
        category === "news" ||
        category === "scrolling_jobs" ||
        category === "home_links"
      )
        continue;

      const tool = tools.find(
        (t) =>
          t.name.toLowerCase().replace(/\s+/g, "-") ===
            toolName.toLowerCase() ||
          t.name.toLowerCase() === toolName.toLowerCase().replace(/-/g, " ")
      );

      if (tool) {
        foundTool = tool;
        foundCategory = category;
        break;
      }
    }

    if (foundTool && foundCategory) {
      // Show the sub-categories for this category
      showSubCategories(foundCategory);
      // Load the tool
      setTimeout(() => {
        loadTool(foundTool.url);
      }, 100);
    }
  }

  // Function to load government services
  function loadGovernmentServices() {
    if (!servicesCards) return;

    const services = data.services;
    servicesCards.innerHTML = "";

    services.forEach((service) => {
      const serviceCard = document.createElement("div");
      serviceCard.className =
        "service-card bg-white p-3 rounded-lg border border-green-200 hover:bg-green-50 hover:border-green-300 transition duration-300 cursor-pointer";
      serviceCard.innerHTML = `
        <div class="flex items-center mb-1">
          <i class="${service.icon} text-2xl mr-3 text-green-600"></i>
          <h4 class="font-semibold text-gray-800 text-sm">${service.name}</h4>
        </div>
      `;

      serviceCard.addEventListener("click", () => {
        showServiceDetails(service);
      });

      servicesCards.appendChild(serviceCard);
    });
  }

  // Function to load home links
  function loadHomeLinks() {
    // Prefer home links from header_links.json (moved), fall back to jobs.json
    const homeLinks =
      headerData && headerData.home_links
        ? headerData.home_links
        : data.home_links || [];
    const homeSection = document.getElementById("home-section");

    if (!homeSection) return;

    homeLinks.forEach((home) => {
      const button = document.createElement("a");
      button.href = home.url;
      button.target = "_blank";
      button.className = `${home.color} text-white w-fit py-1 px-2 rounded-lg shadow-md hover:shadow-lg transition duration-300 flex items-center justify-center font-bold text-sm`;
      button.innerHTML = `
        ${home.name}
      `;
      homeSection.appendChild(button);
    });
  }

  // Function to load social links in footer
  function loadFooterSocialLinks() {
    const socialLinks = headerData && headerData.social_links ? headerData.social_links : [];
    const footerSocialSection = document.getElementById("footer-social-links");

    if (!footerSocialSection) return;

    socialLinks.forEach((social) => {
      const link = document.createElement("a");
      link.href = social.url;
      link.target = "_blank";
      link.className = `${social.color} text-white px-4 py-2 rounded-lg shadow-md hover:shadow-lg transition duration-300 flex items-center justify-center font-semibold`;
      link.innerHTML = `<i class="${social.icon} mr-2"></i>${social.name}`;
      link.title = social.name;
      footerSocialSection.appendChild(link);
    });
  }

  // Function to load jobs
  function loadJobs() {
    const topJobs = data.top_jobs || [];
    const leftJobs = data.left_jobs || [];
    const rightJobs = data.right_jobs || [];
    const topButtons = document.getElementById("jobs-top-buttons");
    const leftSection = document.getElementById("jobs-left-section");
    const rightSection = document.getElementById("jobs-right-section");
    const newsScroll = document.getElementById("news-scroll");
    const jobsScroll = document.getElementById("jobs-scroll");
    const admitcardScroll = document.getElementById("admitcard-scroll");
    const resultsScroll = document.getElementById("results-scroll");
    const newsScrollMobile = document.getElementById("news-scroll-mobile");
    const jobsScrollMobile = document.getElementById("jobs-scroll-mobile");
    const admitcardScrollMobile = document.getElementById("admitcard-scroll-mobile");
    const resultsScrollMobile = document.getElementById("results-scroll-mobile");

    if (
      !topButtons ||
      !leftSection ||
      !rightSection ||
      !newsScroll ||
      !jobsScroll
    )
      return;

    // Top buttons (2 rows of 3)
    // Support a `color` property on title entries. When a title has a color,
    // subsequent job buttons will use a lighter version of that color as
    // their background until the next title.
    let currentTopColor = null;
    topJobs.forEach((job) => {
      if (job.title) {
        // It's a title — update current color if provided
        if (job.color) currentTopColor = job.color;
        else currentTopColor = null;

        const titleDiv = document.createElement("div");
        titleDiv.className = "col-span-full text-left mt-4 py-1";
        titleDiv.innerHTML = `<h3 class="text-2xl font-bold px-2 text-white">${job.title}</h3>`;
        titleDiv.style.backgroundColor = currentTopColor
          ? getLightColor(currentTopColor, 0.05)
          : "transparent";
        topButtons.appendChild(titleDiv);
      } else {
        // It's a button
        const button = document.createElement("div");
        button.className =
          "p-1 ps-2 border-1 hover:shadow-lg transition duration-300 cursor-pointer flex items-center";

        // If a current color is set on the last title, apply a lighter background
        if (currentTopColor) {
          // Try to compute a light variant for hex or rgb colors; otherwise, set as class
          const light = getLightColor(currentTopColor, 0.75);
          if (light) {
            const border = getLightColor(currentTopColor, 0.45);
            if (border) button.style.borderColor = border;
          }
        }

        button.innerHTML = `
          <span class="font-bold text-gray-800 text-xs">${job.name}</span>
        `;
        button.addEventListener("click", () => {
          openJobInNewPage(job);
        });
        topButtons.appendChild(button);
      }
    });

    // Left section
    let currentLeftColor = null;
    leftJobs.forEach((job) => {
      if (job.title) {
        if (job.color) currentLeftColor = job.color;
        else currentLeftColor = null;

        const titleDiv = document.createElement("div");
        titleDiv.className = "col-span-full text-left py-1 mt-4";
        titleDiv.innerHTML = `<h3 class="text-2xl font-bold px-2 text-white">${job.title}</h3>`;
        titleDiv.style.backgroundColor = currentLeftColor
          ? getLightColor(currentLeftColor, 0.05)
          : "transparent";
        leftSection.appendChild(titleDiv);
      } else {
        const button = document.createElement("div");
        button.className =
          "p-1 ps-2 border-1 hover:shadow-lg transition duration-300 cursor-pointer flex items-center";

        if (currentLeftColor) {
          const light = getLightColor(currentLeftColor, 0.75);
          if (light) {
            const border = getLightColor(currentLeftColor, 0.45);
            if (border) button.style.borderColor = border;
          }
        }

        button.innerHTML = `
          <span class="font-bold text-gray-800 text-sm">${job.name}</span>
        `;
        button.addEventListener("click", () => {
          openJobInNewPage(job);
        });
        leftSection.appendChild(button);
      }
    });

    // Right section
    let currentRightColor = null;
    rightJobs.forEach((job) => {
      if (job.title) {
        if (job.color) currentRightColor = job.color;
        else currentRightColor = null;

        const titleDiv = document.createElement("div");
        titleDiv.className = "col-span-full text-left py-1 mt-4";
        titleDiv.innerHTML = `<h3 class="text-2xl font-bold px-2 text-white">${job.title}</h3>`;
        titleDiv.style.backgroundColor = currentRightColor
          ? getLightColor(currentRightColor, 0.05)
          : "transparent";
        rightSection.appendChild(titleDiv);
      } else {
        const button = document.createElement("div");
        button.className =
          "p-1 ps-2 border-1 hover:shadow-lg transition duration-300 cursor-pointer flex items-center";
        button.style.backgroundColor = "#ffffff";
        button.style.borderColor = "#bfdbfe";

        if (currentRightColor) {
          const light = getLightColor(currentRightColor, 0.75);
          if (light) {
            const border = getLightColor(currentRightColor, 0.45);
            if (border) button.style.borderColor = border;
            button.style.color = readableTextColor(currentRightColor);
          }
        }

        button.innerHTML = `
          <span class="font-bold text-gray-800 text-sm">${job.name}</span>
        `;
        button.addEventListener("click", () => {
          openJobInNewPage(job);
        });
        rightSection.appendChild(button);
      }
    });

    // Sample news data
    const newsItems = data.news || [];

    // Populate news scroll (show only first 10 items, no scrolling)
    const newsToShow = newsItems.slice(0, 10);
    newsToShow.forEach((news) => {
      const newsItem = document.createElement("div");
      newsItem.className =
        "bg-blue-50 p-2 rounded border-l-4 border-blue-500 cursor-pointer hover:bg-blue-100 hover:shadow transition duration-300";
      newsItem.innerHTML = `<p class="text-sm font-medium text-gray-700">${news.name}</p>`;
      newsItem.addEventListener("click", () => {
        openJobInNewPage(news);
      });
      newsScroll.appendChild(newsItem);
      if (newsScrollMobile) {
        const mobileNewsItem = newsItem.cloneNode(true);
        mobileNewsItem.addEventListener("click", () => {
          openJobInNewPage(news);
        });
        newsScrollMobile.appendChild(mobileNewsItem);
      }
    });

    // Sample scrolling jobs data
    const scrollingJobs = data.scrolling_jobs || [];

    // Populate jobs scroll (show only first 10 items, no scrolling)
    const jobsToShow = scrollingJobs.slice(0, 10);
    jobsToShow.forEach((job) => {
      const jobItem = document.createElement("div");
      jobItem.className =
        "bg-green-50 p-2 rounded border-l-4 border-green-500 cursor-pointer hover:bg-green-100 hover:shadow transition duration-300";
      jobItem.innerHTML = `<p class="text-sm font-medium text-gray-700">${job.name}</p>`;
      jobItem.addEventListener("click", () => {
        openJobInNewPage(job);
      });
      jobsScroll.appendChild(jobItem);
      if (jobsScrollMobile) {
        const mobileJobItem = jobItem.cloneNode(true);
        mobileJobItem.addEventListener("click", () => {
          openJobInNewPage(job);
        });
        jobsScrollMobile.appendChild(mobileJobItem);
      }
    });

    // Admit card data
    const admitCardItems = data.admit_cards || [];

    // Populate admit card scroll (show only first 10 items, no scrolling)
    const admitCardsToShow = admitCardItems.slice(0, 10);
    admitCardsToShow.forEach((card) => {
      const cardItem = document.createElement("div");
      cardItem.className =
        "bg-orange-50 p-2 rounded border-l-4 border-orange-500 cursor-pointer hover:bg-orange-100 hover:shadow transition duration-300";
      cardItem.innerHTML = `<p class="text-sm font-medium text-gray-700">${card.name}</p>`;
      cardItem.addEventListener("click", () => {
        openJobInNewPage(card);
      });
      if (admitcardScroll) admitcardScroll.appendChild(cardItem);
      if (admitcardScrollMobile) {
        const mobileCardItem = cardItem.cloneNode(true);
        mobileCardItem.addEventListener("click", () => {
          openJobInNewPage(card);
        });
        admitcardScrollMobile.appendChild(mobileCardItem);
      }
    });

    // Results data
    const resultsItems = data.results || [];

    // Populate results scroll (show only first 10 items, no scrolling)
    const resultsToShow = resultsItems.slice(0, 10);
    resultsToShow.forEach((result) => {
      const resultItem = document.createElement("div");
      resultItem.className =
        "bg-purple-50 p-2 rounded border-l-4 border-purple-500 cursor-pointer hover:bg-purple-100 hover:shadow transition duration-300";
      resultItem.innerHTML = `<p class="text-sm font-medium text-gray-700">${result.name}</p>`;
      resultItem.addEventListener("click", () => {
        openJobInNewPage(result);
      });
      if (resultsScroll) resultsScroll.appendChild(resultItem);
      if (resultsScrollMobile) {
        const mobileResultItem = resultItem.cloneNode(true);
        mobileResultItem.addEventListener("click", () => {
          openJobInNewPage(result);
        });
        resultsScrollMobile.appendChild(mobileResultItem);
      }
    });
  }

  // Function to open job in new page with URL params
  function openJobInNewPage(job) {
    const params = new URLSearchParams({
      url: encodeURIComponent(job.url),
      name: encodeURIComponent(job.name),
      job: job.name.toLowerCase().replace(/\s+/g, "-"),
    });
    window.location.href = `view.html?${params.toString()}`;
  }

  // Function to show main categories
  function showMainCategories() {
    if (!mainCategories || !subCategories) return;
    mainCategories.classList.remove("hidden");
    subCategories.classList.add("hidden");

    // Clear URL parameters when going back to main categories
    if (window.location.search) {
      const newUrl = window.location.pathname;
      window.history.replaceState({}, "", newUrl);
    }
  }

  // Function to show sub categories
  function showSubCategories(category) {
    if (!mainCategories || !subCategories) return;

    mainCategories.classList.add("hidden");
    subCategories.classList.remove("hidden");

    // Update title
    const titleIcon = document.querySelector("#sub-category-title i");
    const titleText = document.querySelector("#sub-category-title span");

    titleIcon.className = categoryIcons[category];
    titleText.textContent = categoryNames[category];

    // Clear existing tools
    toolsCards.innerHTML = "";

    // Add tools as cards
    const tools = data[category];
    tools.forEach((tool) => {
      const toolCard = document.createElement("div");
      toolCard.className =
        "tool-card bg-white p-4 rounded-lg border border-gray-200 hover:bg-blue-50 hover:border-blue-300 transition duration-300 cursor-pointer";
      toolCard.innerHTML = `
        <div class="flex items-center mb-1">
          <i class="${tool.icon} text-2xl mr-3 text-gray-600"></i>
          <h4 class="font-semibold text-gray-800 text-sm">${tool.name}</h4>
        </div>
      `;

      if (tool.url) {
        // It's a tool with URL
        toolCard.addEventListener("click", () => {
          const toolSlug = tool.name.toLowerCase().replace(/\s+/g, "-");
          // Update URL with tool parameter
          const newUrl = `${window.location.pathname}?tool=${toolSlug}`;
          window.history.pushState({}, "", newUrl);

          loadTool(tool.url);
        });
      }

      toolsCards.appendChild(toolCard);
    });
  }

  // Function to load tool in iframe
  function loadTool(url) {
    if (!toolIframe || !defaultState || !loadingOverlay) return;

    defaultState.classList.add("hidden");
    toolIframe.classList.remove("hidden");
    loadingOverlay.classList.remove("hidden");
    toolIframe.src = url;

    toolIframe.onload = () => {
      loadingOverlay.classList.add("hidden");
    };
  }

  // Function to show service details in modal
  function showServiceDetails(service) {
    modalServiceContent.innerHTML = `
      <div class="text-center mb-8">
        <h2 class="text-4xl font-bold text-gray-800 mb-4">
          <i class="fas fa-gavel mr-3 text-green-600"></i>
          Service Request
        </h2>
        <div class="w-24 h-1 bg-green-600 mx-auto mb-4"></div>
      </div>

      <div class="mb-8">
        <h3 class="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
          <i class="fas fa-user text-green-500 mr-3"></i>
          Your Information
        </h3>
        <form id="serviceForm">
          <div class="grid md:grid-cols-2 gap-6 mb-6">
            <div>
              <label for="name" class="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
              <input type="text" id="name" name="name" required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <div>
              <label for="phone" class="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
              <input type="tel" id="phone" name="phone" required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
          </div>
          <div class="flex justify-center">
            <button type="submit"
              class="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition duration-300 font-medium">
              <i class="fas fa-paper-plane mr-2"></i>Submit Request
            </button>
          </div>
        </form>
      </div>

      <div class="mb-8">
        <h3 class="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
          <i class="fas fa-info-circle text-blue-500 mr-3"></i>
          Selected Service
        </h3>
        <div class="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
          <p class="text-xl font-medium text-blue-800">${service.name}</p>
        </div>
      </div>

      <div class="mb-8">
        <h3 class="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
          <i class="fas fa-list-check text-purple-500 mr-3"></i>
          Required Documents
        </h3>
        <div class="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded">
          <ul id="documentsList" class="text-gray-700 space-y-2">
            <!-- Documents will be populated based on service -->
          </ul>
        </div>
      </div>

      <div class="mb-8">
        <h3 class="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
          <i class="fas fa-clock text-orange-500 mr-3"></i>
          Processing Time
        </h3>
        <div class="bg-orange-50 border-l-4 border-orange-500 p-4 rounded">
          <p id="processingTime" class="text-gray-700">2-7 working days</p>
        </div>
      </div>
    `;

    // Populate documents
    populateDocuments(service.documents);

    // Handle form submission: POST to Zapier webhook with JSON payload
    const form = modalServiceContent.querySelector("#serviceForm");
    form.addEventListener("submit", (e) => {
      e.preventDefault();

      const name = form.querySelector("#name").value.trim();
      const phone = form.querySelector("#phone").value.trim();

      const payload = {
        name: name,
        number: phone,
        service: service.name,
      };

      const webhookUrl =
        "https://hooks.zapier.com/hooks/catch/25588118/ukxtd3r/";

      // 🔥 CORS-safe Zapier call
      fetch(webhookUrl, {
        method: "POST",
        mode: "no-cors",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })
        .then(async (res) => {
          if (res.ok) {
            // Save to localStorage as fallback
            try {
              const key = "service_requests";
              const existing = JSON.parse(localStorage.getItem(key) || "[]");
              existing.push({
                service: service.name,
                name,
                phone,
                createdAt: new Date().toISOString(),
              });
              localStorage.setItem(key, JSON.stringify(existing));
            } catch (err) {
              console.warn(
                "Could not save service request to localStorage",
                err
              );
            }

            // Close modal and notify user
            serviceModal.classList.add("hidden");
            alert(
              'Your request for "' +
                service.name +
                '" has been submitted. We will contact you soon.'
            );
            form.reset();
          } else {
            const text = await res.text().catch(() => "");
            alert(
              "Submission failed. Please try again later." +
                (text ? "\n" + text : "")
            );
          }
        })
        .catch((err) => {
          console.error("Service request POST failed", err);
          alert(
            "Could not submit your request right now. Please check your connection and try again."
          );
        });
    });

    // Show modal
    serviceModal.classList.remove("hidden");
  }

  // Function to populate documents based on service
  function populateDocuments(documents) {
    const documentsList = modalServiceContent.querySelector("#documentsList");
    documents.forEach((doc) => {
      const li = document.createElement("li");
      li.innerHTML = `<i class="fas fa-check-circle text-green-500 mr-2"></i>${doc}`;
      documentsList.appendChild(li);
    });
  }

  // Helper: convert hex color to RGB object
  function hexToRgb(hex) {
    if (!hex) return null;
    hex = hex.replace("#", "").trim();
    if (hex.length === 3) {
      hex = hex
        .split("")
        .map((c) => c + c)
        .join("");
    }
    if (!/^[0-9a-fA-F]{6}$/.test(hex)) return null;
    const bigint = parseInt(hex, 16);
    return { r: (bigint >> 16) & 255, g: (bigint >> 8) & 255, b: bigint & 255 };
  }

  // Helper: mix color towards white by `mix` fraction (0-1) and return hex string
  function getLightColor(color, mix = 0.7) {
    if (!color) return null;
    color = color.trim();
    // hex
    if (color.startsWith("#")) {
      const rgb = hexToRgb(color);
      if (!rgb) return null;
      const r = Math.round(rgb.r + (255 - rgb.r) * mix);
      const g = Math.round(rgb.g + (255 - rgb.g) * mix);
      const b = Math.round(rgb.b + (255 - rgb.b) * mix);
      return `rgb(${r}, ${g}, ${b})`;
    }

    // rgb(...) format
    const rgbMatch = color.match(
      /rgb\s*\(\s*(\d{1,3})[,\s]+(\d{1,3})[,\s]+(\d{1,3})\s*\)/i
    );
    if (rgbMatch) {
      const r0 = parseInt(rgbMatch[1], 10);
      const g0 = parseInt(rgbMatch[2], 10);
      const b0 = parseInt(rgbMatch[3], 10);
      const r = Math.round(r0 + (255 - r0) * mix);
      const g = Math.round(g0 + (255 - g0) * mix);
      const b = Math.round(b0 + (255 - b0) * mix);
      return `rgb(${r}, ${g}, ${b})`;
    }

    // Not recognized (could be a CSS class like 'bg-red-500')
    return null;
  }

  // Helper: decide readable text color (dark or white) based on original color
  function readableTextColor(color) {
    if (!color) return "#111827"; // default dark gray
    color = color.trim();
    let r, g, b;
    if (color.startsWith("#")) {
      const rgb = hexToRgb(color);
      if (!rgb) return "#111827";
      r = rgb.r;
      g = rgb.g;
      b = rgb.b;
    } else {
      const m = color.match(
        /rgb\s*\(\s*(\d{1,3})[,\s]+(\d{1,3})[,\s]+(\d{1,3})\s*\)/i
      );
      if (m) {
        r = parseInt(m[1], 10);
        g = parseInt(m[2], 10);
        b = parseInt(m[3], 10);
      } else {
        return "#111827";
      }
    }

    // Perceived luminance
    const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
    return luminance > 180 ? "#111827" : "#ffffff";
  }

  // Function to load WhatsApp chat
  async function loadWhatsAppChat() {
    const whatsappBtn = document.getElementById("whatsapp-btn");
    const whatsappPopup = document.getElementById("whatsapp-popup");
    const closeWhatsapp = document.getElementById("close-whatsapp");
    const messagesContainer = document.getElementById("whatsapp-messages");

    if (!whatsappBtn || !whatsappPopup || !messagesContainer) return;

    // Load WhatsApp messages from JSON
    let whatsappData = [];
    try {
      const response = await fetch("whatsapp.json");
      whatsappData = await response.json();
    } catch (error) {
      console.error("Error loading WhatsApp data:", error);
      whatsappData = [
        { message: "Welcome to Top India Services! 👋", link: null },
        { message: "How can we help you today?", link: null }
      ];
    }

    // Populate messages
    whatsappData.forEach((item, index) => {
      const messageDiv = document.createElement("div");
      messageDiv.className = "flex justify-start animate-fadeIn";
      messageDiv.style.animationDelay = `${index * 0.1}s`;

      // Convert URLs and file paths to clickable links
      let messageContent = item.message;
      
      // Convert \n to <br> for multiline support
      messageContent = messageContent.replace(/\n/g, '<br>');
      
      // Detect and convert URLs (http, https)
      messageContent = messageContent.replace(
        /(https?:\/\/[^\s<]+)/gi,
        '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-green-600 font-semibold hover:text-green-700 underline">$1</a>'
      );
      
      // Detect and convert local file paths (.html files)
      messageContent = messageContent.replace(
        /([a-zA-Z0-9_-]+\.html[^\s<]*)/gi,
        '<a href="$1" class="text-green-600 font-semibold hover:text-green-700 underline">$1</a>'
      );

      messageDiv.innerHTML = `
        <div class="bg-white rounded-lg rounded-bl-none shadow p-3 max-w-[85%]">
          <p class="text-gray-800 text-sm whatsapp-message">${messageContent}</p>
        </div>
      `;

      messagesContainer.appendChild(messageDiv);
    });

    // Toggle popup
    whatsappBtn.addEventListener("click", () => {
      whatsappPopup.classList.toggle("hidden");
    });

    closeWhatsapp.addEventListener("click", () => {
      whatsappPopup.classList.add("hidden");
    });

    // Close popup when clicking outside
    document.addEventListener("click", (e) => {
      if (
        !whatsappPopup.contains(e.target) &&
        !whatsappBtn.contains(e.target) &&
        !whatsappPopup.classList.contains("hidden")
      ) {
        whatsappPopup.classList.add("hidden");
      }
    });
  }
});
