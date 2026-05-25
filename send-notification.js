/**
 * TOP SARKARI JOBS — Push Notification Sender (FCM V1 API)
 * ─────────────────────────────────────────────────────────
 * npm install firebase-admin
 * node send-notification.js
 *
 * Place serviceAccountKey.json in same folder before running.
 * Download from: Firebase Console → Project Settings → Service Accounts
 *                → Generate New Private Key
 */

const admin = require('firebase-admin');
const serviceAccount = require('./serviceAccountKey.json');

if (!admin.apps.length) {
  admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });
}
const messaging = admin.messaging();

const SITE = 'https://www.topsarkarijobs.com';
const CATEGORY_URLS = {
  'latest-jobs': SITE + '/section/latest-jobs/',
  'result':      SITE + '/section/results/',
  'admit-card':  SITE + '/section/admit-card/',
  'admission':   SITE + '/section/admission/',
  'answer-key':  SITE + '/section/answer-key/',
};

const CAT_ACTIONS = {
  'latest-jobs': [{action:'view',title:'💼 Jobs Dekho'},{action:'dismiss',title:'✕'}],
  'result':      [{action:'view',title:'🏆 Result Dekho'},{action:'dismiss',title:'✕'}],
  'admit-card':  [{action:'view',title:'🎫 Download'},{action:'dismiss',title:'✕'}],
  'admission':   [{action:'view',title:'🎓 Dekho'},{action:'dismiss',title:'✕'}],
  'answer-key':  [{action:'view',title:'🔑 Dekho'},{action:'dismiss',title:'✕'}],
};

/**
 * sendToTopic(options) — Send to all users subscribed to a category
 * @param {object} options
 *   category  : 'latest-jobs' | 'result' | 'admit-card' | 'admission' | 'answer-key'
 *   title     : Notification title
 *   body      : Notification body text
 *   jobUrl    : (optional) Specific job page URL
 *   imageUrl  : (optional) Large notification image
 */
async function sendToTopic({ category, title, body, jobUrl, imageUrl }) {
  const url = jobUrl || CATEGORY_URLS[category] || SITE + '/';
  const msg = {
    topic: `tsj-${category}`,
    webpush: {
      notification: {
        title, body,
        icon:    SITE + '/icons/icon-192x192.png',
        badge:   SITE + '/icons/icon-96x96.png',
        image:   imageUrl || undefined,
        tag:     `tsj-${category}`,
        renotify: true,
        actions: CAT_ACTIONS[category] || [{action:'view',title:'👁 Dekho'}],
      },
      fcmOptions: { link: url },
    },
    android: {
      priority: 'high',
      notification: {
        title, body,
        color:     '#0d2257',
        tag:       category,
        channelId: 'tsj_jobs',
        imageUrl:  imageUrl || undefined,
        defaultVibrateTimings: true,
      },
      data: { url, category, title, body },
    },
    data: { title, body, url, category, image: imageUrl || '' },
  };

  const id = await messaging.send(msg);
  console.log(`✅ Sent to topic "tsj-${category}" | ID: ${id}`);
  return id;
}

/**
 * sendToToken(token, options) — Send to a specific device (for testing)
 */
async function sendToToken(token, { category, title, body, jobUrl }) {
  const url = jobUrl || CATEGORY_URLS[category] || SITE + '/';
  const msg = {
    token,
    webpush: {
      notification: { title, body,
        icon:  SITE + '/icons/icon-192x192.png',
        badge: SITE + '/icons/icon-96x96.png',
        tag:   `tsj-${category}`, renotify: true,
      },
      fcmOptions: { link: url },
      data: { url, category, title, body },
    },
    data: { title, body, url, category },
  };
  const id = await messaging.send(msg);
  console.log(`✅ Sent to token | ID: ${id}`);
  return id;
}

/**
 * subscribeToTopics(token, categories) — Subscribe FCM token to category topics
 * Call this when saving a new user token
 */
async function subscribeToTopics(token, categories) {
  const all = Array.isArray(categories) ? categories : Object.keys(CATEGORY_URLS);
  for (const cat of all) {
    try {
      await messaging.subscribeToTopic([token], `tsj-${cat}`);
      console.log(`✅ Subscribed to tsj-${cat}`);
    } catch (e) {
      console.warn(`⚠️  tsj-${cat}: ${e.message}`);
    }
  }
}

// ─── USAGE EXAMPLES ──────────────────────────────────────────────────────────
// Edit below and run: node send-notification.js

// 1. Naya Job notification bhejo (ALL subscribers)
sendToTopic({
  category: 'latest-jobs',
  title:    '🔴 New SSC CGL 2026 Notification!',
  body:     'SSC CGL 2026 ka notification aa gaya. 17,727 vacancies. Last date: 18 Aug!',
  jobUrl:   'https://www.topsarkarijobs.com/section/latest-jobs/',
  imageUrl: 'https://www.topsarkarijobs.com/image.png',
});

// 2. Result notification
// sendToTopic({ category:'result', title:'🏆 RRB NTPC Result 2026 Out!',
//   body:'RRB NTPC CBT-1 result declared. Check now!' });

// 3. Admit Card notification
// sendToTopic({ category:'admit-card', title:'🎫 SSC CHSL Admit Card 2026!',
//   body:'SSC CHSL 2026 admit card download karo. Exam: 15 June.' });

// 4. Answer Key notification
// sendToTopic({ category:'answer-key', title:'🔑 UPSC Prelims Answer Key 2026!',
//   body:'UPSC Civil Services Prelims answer key jari. Objection: 10 Jun.' });

// 5. Test to specific device
// sendToToken('YOUR_FCM_TOKEN_HERE', { category:'latest-jobs',
//   title:'🧪 Test', body:'Working!' });

module.exports = { sendToTopic, sendToToken, subscribeToTopics };
