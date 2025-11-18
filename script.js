document.addEventListener("DOMContentLoaded", async () => {
  // Detect current page
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  
  // Load tools data from JSON file
  let toolsData;
  try {
    const response = await fetch('tools.json');
    toolsData = await response.json();
  } catch (error) {
    console.error('Error loading tools data:', error);
    // Fallback empty data
    toolsData = { image: [], pdf: [], video: [], services: [], jobs: [] };
  }

  // Get URL parameters
  const urlParams = new URLSearchParams(window.location.search);
  const jobParam = urlParams.get('job');
  const toolParam = urlParams.get('tool');

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

  // Load content based on current page
  if (currentPage === 'index.html' || currentPage === '') {
    // Jobs page
    loadJobs();
  } else if (currentPage === 'govt-services.html') {
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
  } else if (currentPage === 'tools.html') {
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

    for (const [category, tools] of Object.entries(toolsData)) {
      if (category === 'services' || category === 'jobs') continue;
      
      const tool = tools.find(t => 
        t.name.toLowerCase().replace(/\s+/g, '-') === toolName.toLowerCase() ||
        t.name.toLowerCase() === toolName.toLowerCase().replace(/-/g, ' ')
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
    
    const services = toolsData.services;
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
        showServiceDetails(service.service);
      });

      servicesCards.appendChild(serviceCard);
    });
  }

  // Function to load jobs
  function loadJobs() {
    const jobs = toolsData.jobs;
    const topButtons = document.getElementById("jobs-top-buttons");
    const otherButtons = document.getElementById("jobs-other-buttons");

    if (!topButtons || !otherButtons) return;

    // Group jobs by position
    const topJobs = jobs.filter(job => job.position === 'top');
    const otherJobs = jobs.filter(job => job.position !== 'top');

    // Top buttons
    topJobs.forEach(job => {
      const button = document.createElement("div");
      button.className = "bg-white p-4 rounded-lg border-2 border-blue-200 hover:bg-blue-50 hover:border-blue-400 hover:shadow-lg transition duration-300 cursor-pointer flex items-center justify-center text-center";
      button.innerHTML = `
        <span class="font-semibold text-gray-800 text-base">${job.name}</span>
      `;
      button.addEventListener("click", () => {
        openJobInNewPage(job);
      });
      topButtons.appendChild(button);
    });

    // Other buttons (left and right)
    otherJobs.forEach(job => {
      const button = document.createElement("div");
      button.className = "bg-white p-4 rounded-lg border-2 border-blue-200 hover:bg-blue-50 hover:border-blue-400 hover:shadow-lg transition duration-300 cursor-pointer flex items-center justify-center text-center";
      button.innerHTML = `
        <span class="font-semibold text-gray-800 text-base">${job.name}</span>
      `;
      button.addEventListener("click", () => {
        openJobInNewPage(job);
      });
      otherButtons.appendChild(button);
    });
  }

  // Function to open job in new page with URL params
  function openJobInNewPage(job) {
    const params = new URLSearchParams({
      url: encodeURIComponent(job.url),
      name: encodeURIComponent(job.name),
      job: job.name.toLowerCase().replace(/\s+/g, '-')
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
      window.history.replaceState({}, '', newUrl);
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
    const tools = toolsData[category];
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
          const toolSlug = tool.name.toLowerCase().replace(/\s+/g, '-');
          // Update URL with tool parameter
          const newUrl = `${window.location.pathname}?tool=${toolSlug}`;
          window.history.pushState({}, '', newUrl);
          
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
  function showServiceDetails(serviceName) {
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
          <p class="text-xl font-medium text-blue-800">${serviceName}</p>
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
    populateDocuments(serviceName);

    // Handle form submission
    const form = modalServiceContent.querySelector("#serviceForm");
    form.addEventListener("submit", (e) => {
      e.preventDefault();

      const name = form.querySelector("#name").value;
      const phone = form.querySelector("#phone").value;

      const params = new URLSearchParams({
        service: serviceName,
        name: name,
        phone: phone,
      });

      // Close modal before redirecting
      serviceModal.classList.add("hidden");
      window.location.href = `service.html?${params.toString()}`;
    });

    // Show modal
    serviceModal.classList.remove("hidden");
  }

  // Function to populate documents based on service
  function populateDocuments(serviceName) {
    const documentsList = modalServiceContent.querySelector("#documentsList");
    let documents = [];

    if (serviceName.includes('पैन')) {
      documents = [
        'आधार कार्ड की फोटोकॉपी',
        'पासपोर्ट साइज फोटो (2 कॉपी)',
        'मोबाइल नंबर',
        'ईमेल आईडी'
      ];
    } else if (serviceName.includes('वोटर')) {
      documents = [
        'आधार कार्ड',
        'पासपोर्ट साइज फोटो',
        'मोबाइल नंबर',
        'ईमेल आईडी (वैकल्पिक)'
      ];
    } else if (serviceName.includes('पासपोर्ट')) {
      documents = [
        'आधार कार्ड',
        'पैन कार्ड',
        'जन्म प्रमाण पत्र',
        '10वीं की मार्कशीट',
        'पासपोर्ट साइज फोटो (6 कॉपी)',
        'मोबाइल नंबर'
      ];
    } else if (serviceName.includes('प्रमाण पत्र') || serviceName.includes('Certificate')) {
      documents = [
        'आधार कार्ड',
        'जन्म प्रमाण पत्र',
        'कास्ट प्रमाण पत्र (यदि लागू)',
        'पासपोर्ट साइज फोटो',
        'मोबाइल नंबर'
      ];
    } else if (serviceName.includes('पेंशन')) {
      documents = [
        'आधार कार्ड',
        'बैंक पासबुक',
        'मोबाइल नंबर',
        'फोटो'
      ];
    } else {
      documents = [
        'आधार कार्ड',
        'पासपोर्ट साइज फोटो',
        'मोबाइल नंबर',
        'संबंधित दस्तावेज'
      ];
    }

    documents.forEach(doc => {
      const li = document.createElement('li');
      li.innerHTML = `<i class="fas fa-check-circle text-green-500 mr-2"></i>${doc}`;
      documentsList.appendChild(li);
    });
  }

});
