/**
 * SECURE FALLBACK LOGIC FOR GOOGLE CRAWLER
 * ==========================================
 * JobPosting Schema Generator with intelligent fallback for missing/invalid AI-extracted data
 * Ensures valid structured data even when source data is incomplete or malformed
 */

class JobPostingSchemaGenerator {
  constructor(config = {}) {
    this.config = {
      defaultValidThroughDays: 180, // Safe fallback: 6 months from today
      defaultRegion: 'Delhi',
      defaultPostalCode: '110001',
      minSalary: 21700,
      maxSalary: 69100,
      ...config
    };
    
    // Regex patterns for validation
    this.patterns = {
      date: /^\d{4}-\d{2}-\d{2}$/, // ISO 8601
      pincode: /^\d{6}$/,
      salary: /^\d+$/,
      email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    };
    
    // Blacklist of invalid/placeholder values
    this.invalidValues = [
      'null', 'none', 'nil', 'na', 'n/a', 'pending', 
      'as per schedule', 'as per notification', 'tbd',
      'no salary', 'not applicable', '', undefined, null
    ];
  }

  /**
   * Clean and validate a value
   */
  clean(value) {
    if (!value) return null;
    
    const str = String(value).trim().toLowerCase();
    return this.invalidValues.includes(str) ? null : String(value).trim();
  }

  /**
   * FALLBACK 1: Valid Through Date (ISO 8601 format)
   * Priority order:
   * 1. AI-extracted last_date
   * 2. Current date + 6 months
   */
  getValidThrough(job) {
    const aiData = job.ai_extracted_structured_data || {};
    let validThrough = this.clean(aiData.last_date || aiData.valid_through);
    
    // Validate ISO 8601 format
    if (validThrough && this.patterns.date.test(validThrough)) {
      const date = new Date(validThrough);
      if (!isNaN(date.getTime()) && date > new Date()) {
        return validThrough; // Valid date in future
      }
    }
    
    // Fallback: 6 months from now
    const fallbackDate = new Date();
    fallbackDate.setDate(fallbackDate.getDate() + this.config.defaultValidThroughDays);
    return fallbackDate.toISOString().split('T')[0];
  }

  /**
   * FALLBACK 2: Job Location + Postal Code
   * Priority order for location:
   * 1. AI-extracted job_location
   * 2. Manual job_location field
   * 3. State field
   * 4. Default (Delhi)
   * 
   * Priority order for postal code:
   * 1. AI-extracted postal_code (must be 6 digits)
   * 2. Location-based mapping
   * 3. Default (110001 - Delhi)
   */
  getLocationAndPostalCode(job) {
    const aiData = job.ai_extracted_structured_data || {};
    
    // Extract location
    let location = this.clean(
      aiData.job_location || 
      job.job_location || 
      job.state || 
      job.location
    );
    
    if (!location) {
      location = this.config.defaultRegion;
    }
    
    // Extract postal code
    let postalCode = this.clean(aiData.postal_code);
    
    // Validate postal code format (6 digits)
    if (!postalCode || !this.patterns.pincode.test(postalCode)) {
      postalCode = this.getPostalCodeForLocation(location);
    }
    
    return { location, postalCode };
  }

  /**
   * Get postal code for a given location
   * Maps Indian states to representative postal codes
   */
  getPostalCodeForLocation(location) {
    if (!location) return '110001';
    
    const locationMap = {
      'delhi': '110001',
      'haryana': '121001',
      'punjab': '160001',
      'rajasthan': '302001',
      'bihar': '800001',
      'uttar pradesh': '201301',
      'maharashtra': '400001',
      'karnataka': '560001',
      'tamil nadu': '600001',
      'telangana': '500001',
      'west bengal': '700001',
      'gujarat': '380001',
      'madhya pradesh': '450001',
      'kerala': '682001',
      'odisha': '751001',
      'jharkhand': '813301',
      'assam': '781001'
    };
    
    const key = location.toLowerCase().trim();
    return locationMap[key] || '110001'; // Default Delhi
  }

  /**
   * FALLBACK 3: Salary Range
   * Priority order:
   * 1. AI-extracted salary_range (must be numeric)
   * 2. Parsed from description/qualifications
   * 3. Default safe range (21700-69100, typical govt salary)
   * 
   * Safety: Always use valid numeric ranges
   */
  getSalaryRange(job) {
    const aiData = job.ai_extracted_structured_data || {};
    
    let minSal = null;
    let maxSal = null;
    
    // Try to extract from AI data
    if (aiData.salary_range) {
      const match = String(aiData.salary_range).match(/(\d+)\s*-\s*(\d+)/);
      if (match) {
        minSal = parseInt(match[1]);
        maxSal = parseInt(match[2]);
      }
    }
    
    // Fallback: Try min_salary / max_salary fields
    if (!minSal && aiData.min_salary) {
      minSal = parseInt(String(aiData.min_salary).replace(/\D/g, ''));
    }
    if (!maxSal && aiData.max_salary) {
      maxSal = parseInt(String(aiData.max_salary).replace(/\D/g, ''));
    }
    
    // Validate extracted salaries
    if (minSal && maxSal && minSal > 0 && maxSal > minSal && maxSal <= 1000000) {
      return { minSal, maxSal };
    }
    
    // Fallback: Default safe range
    return {
      minSal: this.config.minSalary,
      maxSal: this.config.maxSalary
    };
  }

  /**
   * Generate complete JobPosting schema with fallbacks
   */
  generateSchema(job) {
    if (!job || !job.basic_details) {
      console.error('[Schema] Invalid job object');
      return null;
    }
    
    const bd = job.basic_details;
    const { location, postalCode } = this.getLocationAndPostalCode(job);
    const { minSal, maxSal } = this.getSalaryRange(job);
    const validThrough = this.getValidThrough(job);
    
    // Job title (required)
    const jobTitle = this.clean(bd.job_title || bd.title);
    if (!jobTitle) {
      console.error('[Schema] Missing job title');
      return null;
    }
    
    // Organization (required)
    const org = this.clean(bd.organization_name || bd.organization);
    if (!org) {
      console.error('[Schema] Missing organization');
      return null;
    }
    
    return {
      '@context': 'https://schema.org',
      '@type': 'JobPosting',
      
      // Required fields
      'title': jobTitle,
      'description': this.clean(bd.description || bd.short_information || jobTitle),
      'hiringOrganization': {
        '@type': 'Organization',
        'name': org,
        'sameAs': this.clean(bd.organization_website || bd.official_website) || undefined
      },
      'jobLocation': {
        '@type': 'Place',
        'address': {
          '@type': 'PostalAddress',
          'addressRegion': location,
          'postalCode': postalCode,
          'addressCountry': 'IN'
        }
      },
      
      // Date range
      'datePosted': this.clean(bd.posting_date || bd.notification_date) || 
                    new Date().toISOString().split('T')[0],
      'validThrough': validThrough,
      
      // Salary
      'baseSalary': {
        '@type': 'PriceSpecification',
        'priceCurrency': 'INR',
        'price': `${minSal}-${maxSal}`,
        'priceComponentType': 'https://schema.org/SalaryUnitType#Monthly'
      },
      
      // Employment details
      'employmentType': this.clean(bd.job_type || bd.employment_type) || 'FullTime',
      'jobLocationType': location && location.toLowerCase().includes('pan-india') ? 
                        'LocationPreference' : 'Physical',
      
      // Application info
      'applicationContact': this.buildApplicationContact(bd),
      
      // Experience level (if available)
      ...(this.clean(bd.qualification) && {
        'qualifications': this.clean(bd.qualification)
      }),
      
      // Additional safe data
      ...(this.clean(bd.post_name) && {
        'alternateName': this.clean(bd.post_name)
      }),
      
      // Meta
      'url': this.clean(bd.apply_link || bd.official_website) || undefined,
      'inLanguage': 'en-IN'
    };
  }

  /**
   * Build safe application contact object
   */
  buildApplicationContact(bd) {
    const contact = {
      '@type': 'ContactPoint',
      'contactType': 'HR',
      'areaServed': 'IN'
    };
    
    if (this.patterns.email.test(bd.contact_email || '')) {
      contact.email = this.clean(bd.contact_email);
    }
    
    if (this.clean(bd.contact_phone)) {
      contact.telephone = this.clean(bd.contact_phone);
    }
    
    return Object.keys(contact).length > 2 ? contact : undefined;
  }

  /**
   * Validate generated schema
   */
  validateSchema(schema) {
    if (!schema) return false;
    
    const required = ['title', 'description', 'hiringOrganization', 'jobLocation'];
    const errors = [];
    
    for (const field of required) {
      if (!schema[field]) {
        errors.push(`Missing required field: ${field}`);
      }
    }
    
    // Validate salary range
    if (schema.baseSalary) {
      const [min, max] = schema.baseSalary.price.split('-').map(Number);
      if (min > max || min < 0) {
        errors.push('Invalid salary range');
      }
    }
    
    // Validate date
    if (schema.validThrough) {
      const date = new Date(schema.validThrough);
      if (isNaN(date.getTime())) {
        errors.push('Invalid date format');
      }
    }
    
    if (errors.length > 0) {
      console.warn('[Schema] Validation errors:', errors);
      return false;
    }
    
    return true;
  }

  /**
   * Inject schema into HTML page
   */
  injectSchema(schema, elementId = null) {
    if (!this.validateSchema(schema)) {
      console.error('[Schema] Failed validation, not injecting');
      return false;
    }
    
    try {
      const scriptTag = document.createElement('script');
      scriptTag.type = 'application/ld+json';
      scriptTag.textContent = JSON.stringify(schema);
      
      if (elementId && document.getElementById(elementId)) {
        document.getElementById(elementId).appendChild(scriptTag);
      } else {
        document.head.appendChild(scriptTag);
      }
      
      console.log('[Schema] Injected successfully');
      return true;
    } catch (error) {
      console.error('[Schema] Injection failed:', error);
      return false;
    }
  }
}

// Usage Example:
// ===============
// const generator = new JobPostingSchemaGenerator();
// const schema = generator.generateSchema(jobData);
// generator.injectSchema(schema);

// Export for use in Node.js or bundlers
if (typeof module !== 'undefined' && module.exports) {
  module.exports = JobPostingSchemaGenerator;
}
