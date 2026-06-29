/**
 * send-fcm.js — Firebase FCM Push Notification Sender
 * =====================================================
 * Called by send-push-notification.yml via: node .github/workflows/send-fcm.js
 *
 * P4 FIX: ALL config read from process.env — NO shell interpolation
 * Apostrophes in job titles cannot break this script
 *
 * Required env vars:
 *   SA_JSON      — Firebase Admin SDK service account JSON string
 *   NOTIF_TITLE  — Notification title (may contain apostrophes, quotes, etc.)
 *   NOTIF_BODY   — Notification body
 *   NOTIF_URL    — Target URL (optional, defaults to section URL)
 *   NOTIF_CAT    — Category: latest-jobs | result | admit-card | answer-key | admission
 */

'use strict';

const admin = require('firebase-admin');

const SITE = 'https://www.topsarkarijobs.com';

// ── Topic map ──────────────────────────────────────────────────────────
const TOPIC_MAP = {
  'latest-jobs': 'tsj-latest-jobs',
  'result':      'tsj-result',
  'admit-card':  'tsj-admit-card',
  'answer-key':  'tsj-answer-key',
  'admission':   'tsj-admission',
};

// ── Default URLs per category ──────────────────────────────────────────
const CAT_URLS = {
  'latest-jobs': `${SITE}/section/latest-jobs/`,
  'result':      `${SITE}/section/results/`,
  'admit-card':  `${SITE}/section/admit-card/`,
  'answer-key':  `${SITE}/section/answer-key/`,
  'admission':   `${SITE}/section/admission/`,
};

// ── Read config from environment (safe — no shell injection) ───────────
const saJson    = process.env.SA_JSON    || '';
const title     = process.env.NOTIF_TITLE || '🔔 New Update on Top Sarkari Jobs!';
const body      = process.env.NOTIF_BODY  || 'Nayi sarkari vacancy aa gayi. Abhi check karo!';
const category  = process.env.NOTIF_CAT  || 'latest-jobs';
const topic     = TOPIC_MAP[category]    || 'tsj-latest-jobs';
const url       = (process.env.NOTIF_URL || '').trim() || CAT_URLS[category] || `${SITE}/`;

// ── Validate ───────────────────────────────────────────────────────────
if (!saJson) {
  console.error('❌ FIREBASE_SERVICE_ACCOUNT_JSON (SA_JSON) is not set!');
  process.exit(1);
}

// ── Init Firebase Admin ────────────────────────────────────────────────
let sa;
try {
  sa = JSON.parse(saJson);
} catch (e) {
  console.error('❌ SA_JSON parse failed:', e.message);
  process.exit(1);
}

try {
  admin.initializeApp({ credential: admin.credential.cert(sa) });
} catch (e) {
  console.error('❌ Firebase init failed:', e.message);
  process.exit(1);
}

const messaging = admin.messaging();

// ── Build FCM message ──────────────────────────────────────────────────
const shortTitle = title.length > 65 ? title.slice(0, 62) + '...' : title;
const shortBody  = body.length  > 120 ? body.slice(0, 117) + '...' : body;

const message = {
  topic,
  webpush: {
    notification: {
      title:              shortTitle,
      body:               shortBody,
      icon:               `${SITE}/icons/icon-192x192.png`,
      badge:              `${SITE}/icons/icon-96x96.png`,
      tag:                `tsj-${category}`,
      renotify:           true,
      requireInteraction: false,
      vibrate:            [150, 80, 150],
      actions: [
        { action: 'view', title: '🔔 अभी साइट विजिट करें मौका ना खोयें' },
      ],
    },
    fcmOptions: { link: url },
  },
  android: {
    priority: 'high',
    notification: {
      title:     shortTitle,
      body:      shortBody,
      color:     '#0d2257',
      tag:       `tsj-${category}`,
      channelId: 'tsj_jobs',
      defaultVibrateTimings: true,
    },
    data: { url, category, title: shortTitle, body: shortBody },
  },
  data: {
    title:    shortTitle,
    body:     shortBody,
    url,
    category,
  },
};

// ── Send ───────────────────────────────────────────────────────────────
console.log('📣 Sending FCM notification...');
console.log(`   Topic:    ${topic}`);
console.log(`   Title:    ${shortTitle}`);
console.log(`   URL:      ${url}`);

messaging.send(message)
  .then(id => {
    console.log('✅ Notification sent successfully!');
    console.log(`   FCM Message ID: ${id}`);
    process.exit(0);
  })
  .catch(err => {
    // No subscribers is normal — exit 0, not error
    if (err.code === 'messaging/registration-token-not-registered' ||
        err.message.includes('no-topic-subscriptions') ||
        err.message.includes('UNREGISTERED')) {
      console.warn('⚠️ No active subscribers for topic:', topic);
      console.log('   (Normal if users haven\'t subscribed yet)');
      process.exit(0);
    }
    console.error('❌ FCM send failed:', err.message);
    console.error('   Code:', err.code || 'unknown');
    process.exit(0); // exit 0 — don't fail the workflow for push failures
  });
