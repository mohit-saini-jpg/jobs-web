/**
 * TopSarkariJobs — CSC Govt Services Page Script
 */
(function () {
  'use strict';

  var SERVICES = [
    { name: 'Aadhaar Card Services', icon: 'fa-id-card', color: '#1d4ed8', desc: 'Aadhaar enrollment, update, correction & download.', links: [{ label: 'UIDAI Portal', url: 'https://uidai.gov.in' }, { label: 'My Aadhaar', url: 'https://myaadhaar.uidai.gov.in' }] },
    { name: 'PAN Card Services', icon: 'fa-credit-card', color: '#15803d', desc: 'Apply new PAN, correction, reprint via NSDL/UTI.', links: [{ label: 'NSDL PAN', url: 'https://www.onlineservices.nsdl.com/paam/endUserRegisterContact.html' }, { label: 'UTI PAN', url: 'https://www.utiitsl.com/UTIITSL_SITE/pan/' }] },
    { name: 'Passport Services', icon: 'fa-passport', color: '#7c3aed', desc: 'Apply, renew, track passport & appointment booking.', links: [{ label: 'Passport Seva', url: 'https://www.passportindia.gov.in' }] },
    { name: 'Voter ID / EPIC Card', icon: 'fa-vote-yea', color: '#ea580c', desc: 'Voter registration, correction, download EPIC card.', links: [{ label: 'Voter Helpline', url: 'https://voterportal.eci.gov.in' }, { label: 'NVSP', url: 'https://www.nvsp.in' }] },
    { name: 'Income Certificate', icon: 'fa-file-invoice', color: '#0f766e', desc: 'Apply income, domicile & caste certificate online.', links: [{ label: 'Umang App', url: 'https://web.umang.gov.in' }, { label: 'DigiLocker', url: 'https://www.digilocker.gov.in' }] },
    { name: 'Driving Licence Services', icon: 'fa-car', color: '#be123c', desc: 'Apply DL, learner licence, renewal & RC services.', links: [{ label: 'Parivahan', url: 'https://parivahan.gov.in' }, { label: 'Sarathi', url: 'https://sarathi.parivahan.gov.in' }] },
    { name: 'PM Kisan Samman Nidhi', icon: 'fa-seedling', color: '#16a34a', desc: 'Check PM Kisan status, eKYC & beneficiary list.', links: [{ label: 'PM Kisan Portal', url: 'https://pmkisan.gov.in' }] },
    { name: 'Ayushman Bharat (PMJAY)', icon: 'fa-hospital', color: '#0891b2', desc: 'Health card download, hospital list & eligibility check.', links: [{ label: 'Ayushman Portal', url: 'https://pmjay.gov.in' }, { label: 'Beneficiary Portal', url: 'https://beneficiary.nha.gov.in' }] },
    { name: 'Ration Card Services', icon: 'fa-wheat-awn', color: '#b45309', desc: 'Apply, update, download ration card & check status.', links: [{ label: 'NFSA Portal', url: 'https://nfsa.gov.in' }, { label: 'One Nation One Ration', url: 'https://impds.nic.in' }] },
    { name: 'Birth & Death Certificate', icon: 'fa-certificate', color: '#6d28d9', desc: 'Register and download birth/death certificates.', links: [{ label: 'CRS Portal', url: 'https://crsorgi.gov.in' }] },
    { name: 'DigiLocker Services', icon: 'fa-lock', color: '#1d4ed8', desc: 'Store & share digital documents — marksheet, DL, Aadhaar.', links: [{ label: 'DigiLocker', url: 'https://www.digilocker.gov.in' }] },
    { name: 'e-Shram Card', icon: 'fa-hard-hat', color: '#ea580c', desc: 'Register for unorganised workers e-Shram card.', links: [{ label: 'e-Shram Portal', url: 'https://eshram.gov.in' }] },
  ];

  function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function renderServices() {
    var container = document.getElementById('servicesList');
    if (!container) return;

    var html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;padding:4px 0;">';

    SERVICES.forEach(function (svc) {
      var linksHtml = svc.links.map(function (lk) {
        return '<a href="' + esc(lk.url) + '" target="_blank" rel="noopener noreferrer" '
          + 'style="display:inline-flex;align-items:center;gap:5px;padding:6px 12px;border-radius:6px;'
          + 'background:' + esc(svc.color) + ';color:#fff;text-decoration:none;font-weight:600;font-size:.75rem;margin:3px 4px 3px 0;transition:.15s;">'
          + '<i class="fa-solid fa-external-link-alt" style="font-size:.65rem;"></i>' + esc(lk.label) + '</a>';
      }).join('');

      html += '<div style="background:#fff;border:1px solid #e9f0f5;border-radius:14px;overflow:hidden;box-shadow:0 4px 12px -4px rgba(0,0,0,.07);transition:.18s;" '
        + 'onmouseover="this.style.transform=\'translateY(-2px)\';this.style.boxShadow=\'0 10px 24px -6px rgba(0,0,0,.1)\'" '
        + 'onmouseout="this.style.transform=\'\';this.style.boxShadow=\'0 4px 12px -4px rgba(0,0,0,.07)\'">'
        + '<div style="background:' + esc(svc.color) + ';padding:14px 16px;display:flex;align-items:center;gap:12px;">'
        + '<div style="width:40px;height:40px;background:rgba(255,255,255,.2);border-radius:10px;display:flex;align-items:center;justify-content:center;">'
        + '<i class="fa-solid ' + esc(svc.icon) + '" style="color:#fff;font-size:1.1rem;"></i></div>'
        + '<span style="color:#fff;font-weight:700;font-size:.95rem;">' + esc(svc.name) + '</span>'
        + '</div>'
        + '<div style="padding:14px 16px;">'
        + '<p style="font-size:.83rem;color:#374151;line-height:1.65;margin-bottom:12px;">' + esc(svc.desc) + '</p>'
        + '<div>' + linksHtml + '</div>'
        + '</div></div>';
    });

    html += '</div>';
    container.innerHTML = html;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderServices);
  } else {
    renderServices();
  }
})();
