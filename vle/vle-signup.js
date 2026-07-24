/* Shared "VLE profile fields" form (state/district/center details) used by
   BOTH /vle/signup (fresh registration) and /vle/dashboard (finishing a
   profile after confirming email, for an account that has no vle_profiles
   row yet). Keeping this in one place means the two entry points can never
   drift out of sync with each other.

   STATE_DISTRICTS mirrors VLE_STATE_DISTRICTS in generate_all.py exactly —
   keep both in sync if the supported states/districts ever change. */
(function (global) {
  var STATE_DISTRICTS = {"Haryana": ["Ambala", "Bhiwani", "Charkhi Dadri", "Faridabad", "Fatehabad", "Gurugram", "Hisar", "Jhajjar", "Jind", "Kaithal", "Karnal", "Kurukshetra", "Mahendragarh", "Nuh", "Palwal", "Panchkula", "Panipat", "Rewari", "Rohtak", "Sirsa", "Sonipat", "Yamunanagar"], "Delhi": ["Central Delhi", "Central North Delhi", "East Delhi", "New Delhi", "North Delhi", "North East Delhi", "North West Delhi", "Old Delhi", "Outer North Delhi", "South Delhi", "South East Delhi", "South West Delhi", "West Delhi"], "Punjab": ["Amritsar", "Barnala", "Bathinda", "Faridkot", "Fatehgarh Sahib", "Firozpur", "Fazilka", "Gurdaspur", "Hoshiarpur", "Jalandhar", "Kapurthala", "Ludhiana", "Malerkotla", "Mansa", "Moga", "Sri Muktsar Sahib", "Pathankot", "Patiala", "Rupnagar", "Sahibzada Ajit Singh Nagar", "Sangrur", "Shaheed Bhagat Singh Nagar", "Tarn Taran"], "Uttar Pradesh": ["Agra", "Aligarh", "Ambedkar Nagar", "Amethi", "Amroha", "Auraiya", "Ayodhya", "Azamgarh", "Budaun", "Bagpat", "Bahraich", "Ballia", "Balrampur", "Banda", "Barabanki", "Bareilly", "Basti", "Bhadohi", "Bijnor", "Bulandshahr", "Chandauli", "Chitrakoot", "Deoria", "Etah", "Etawah", "Farrukhabad", "Fatehpur", "Firozabad", "Gautam Buddha Nagar", "Ghaziabad", "Ghazipur", "Gonda", "Gorakhpur", "Hamirpur", "Hapur", "Hardoi", "Hathras", "Jalaun", "Jaunpur", "Jhansi", "Kannauj", "Kanpur Dehat", "Kanpur Nagar", "Kasganj", "Kaushambi", "Kushinagar", "Lakhimpur Kheri", "Lalitpur", "Lucknow", "Maharajganj", "Mahoba", "Mainpuri", "Mathura", "Mau", "Meerut", "Mirzapur", "Moradabad", "Muzaffarnagar", "Pilibhit", "Pratapgarh", "Prayagraj", "Rae Bareli", "Rampur", "Saharanpur", "Sant Kabir Nagar", "Sambhal", "Shahjahanpur", "Shamli", "Shravasti", "Siddharthnagar", "Sitapur", "Sonbhadra", "Sultanpur", "Unnao", "Varanasi"], "Rajasthan": ["Ajmer", "Alwar", "Balotra", "Banswara", "Baran", "Barmer", "Beawar", "Bharatpur", "Bhilwara", "Bikaner", "Bundi", "Chittorgarh", "Churu", "Dausa", "Deeg", "Didwana-Kuchaman", "Dholpur", "Dungarpur", "Hanumangarh", "Jaipur", "Jaisalmer", "Jalore", "Jhalawar", "Jhunjhunu", "Jodhpur", "Karauli", "Khairthal-Tijara", "Kota", "Kotputli-Behror", "Nagaur", "Pali", "Phalodi", "Pratapgarh", "Rajsamand", "Salumbar", "Sawai Madhopur", "Sikar", "Sirohi", "Sri Ganganagar", "Tonk", "Udaipur"]};

  function fieldsHtml() {
    return '' +
      '<div class="vle-field"><label for="vleSuState">State</label>' +
      '<select id="vleSuState" required></select></div>' +
      '<div class="vle-field"><label for="vleSuDistrict">District</label>' +
      '<select id="vleSuDistrict" required></select></div>' +
      '<div class="vle-field"><label for="vleSuCenter">CSC / Center Name</label>' +
      '<input type="text" id="vleSuCenter" required maxlength="120" placeholder="Jaise: Verma Photostat &amp; Bhima Center"></div>' +
      '<div class="vle-field"><label for="vleSuOwner">Owner Name</label>' +
      '<input type="text" id="vleSuOwner" maxlength="80" placeholder="Aapka naam"></div>' +
      '<div class="vle-field"><label for="vleSuAddress">Shop Address</label>' +
      '<textarea id="vleSuAddress" rows="2" maxlength="300" placeholder="Poora address"></textarea></div>' +
      '<div class="vle-field"><label for="vleSuPhone">Contact Phone</label>' +
      '<input type="tel" id="vleSuPhone" maxlength="10" placeholder="10-digit number"></div>' +
      '<div class="vle-field"><label for="vleSuWhatsapp">WhatsApp Number</label>' +
      '<input type="tel" id="vleSuWhatsapp" required maxlength="10" placeholder="10-digit number"></div>';
  }

  function populateStateDropdown(sel) {
    sel.innerHTML = '<option value="">-- State chunein --</option>';
    Object.keys(STATE_DISTRICTS).forEach(function (st) {
      var o = document.createElement('option');
      o.value = st; o.textContent = st;
      sel.appendChild(o);
    });
  }

  function populateDistrictDropdown(sel, st) {
    if (!st || !STATE_DISTRICTS[st]) {
      sel.innerHTML = '<option value="">-- Pehle state chunein --</option>';
      return;
    }
    sel.innerHTML = '<option value="">-- District chunein --</option>';
    STATE_DISTRICTS[st].forEach(function (d) {
      var o = document.createElement('option');
      o.value = d; o.textContent = d;
      sel.appendChild(o);
    });
  }

  // Populates + wires the state->district dependent dropdowns. Call once
  // right after injecting fieldsHtml() into the DOM.
  function wireDropdowns(container) {
    var stSel = container.querySelector('#vleSuState');
    var dSel = container.querySelector('#vleSuDistrict');
    populateStateDropdown(stSel);
    populateDistrictDropdown(dSel, '');
    stSel.addEventListener('change', function () { populateDistrictDropdown(dSel, stSel.value); });
  }

  function readFields(container) {
    return {
      state: container.querySelector('#vleSuState').value,
      district: container.querySelector('#vleSuDistrict').value,
      center_name: container.querySelector('#vleSuCenter').value.trim(),
      owner_name: container.querySelector('#vleSuOwner').value.trim(),
      shop_address: container.querySelector('#vleSuAddress').value.trim(),
      contact_phone: container.querySelector('#vleSuPhone').value.trim(),
      whatsapp_number: container.querySelector('#vleSuWhatsapp').value.trim(),
    };
  }

  // Auto-assigns the next free slot for state+district (via the
  // next_vle_slot RPC — see supabase/vle_signup_approval_migration.sql) and
  // inserts the profile row as pending approval. Retries a couple times if
  // a concurrent signup for the same district wins the race on that slot
  // number (unique_violation, Postgres code 23505).
  async function createVleProfile(client, userId, f) {
    if (!f.state || !f.district) return { error: { message: 'State aur District dono chunein.' } };
    if (!f.center_name) return { error: { message: 'Center/CSC ka naam zaroori hai.' } };
    if (!f.whatsapp_number || f.whatsapp_number.length < 10) return { error: { message: 'WhatsApp number zaroori hai (10 digit).' } };

    for (var attempt = 0; attempt < 3; attempt++) {
      var slotRes = await client.rpc('next_vle_slot', { p_state: f.state, p_district: f.district });
      if (slotRes.error) return { error: slotRes.error };
      var slot = slotRes.data;
      var ins = await client.from('vle_profiles').insert({
        id: userId, state: f.state, district: f.district, slot: slot,
        center_name: f.center_name, owner_name: f.owner_name || null,
        shop_address: f.shop_address || null, contact_phone: f.contact_phone || null,
        whatsapp_number: f.whatsapp_number, is_approved: false,
      });
      if (!ins.error) return { data: { slot: slot } };
      if (ins.error.code !== '23505') return { error: ins.error }; // not a slot race — real failure
    }
    return { error: { message: 'Slot assign nahi ho paya, thodi der baad dubara try karein.' } };
  }

  global.TsjVleSignup = {
    fieldsHtml: fieldsHtml,
    wireDropdowns: wireDropdowns,
    readFields: readFields,
    createVleProfile: createVleProfile,
  };
})(window);
