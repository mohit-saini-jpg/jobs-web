# 🔔 Push Notification Setup — Top Sarkari Jobs
## FCM V1 API | Project: job-portal-750e0

---

## ✅ Files Already Configured (Ready to Deploy)

| File | Status |
|------|--------|
| `sw.js` | ✅ FCM push handler ready |
| `tsj-push.js` | ✅ Firebase config + VAPID key set |
| `index.html` + 8 other HTML files | ✅ Script tag added |
| `.github/workflows/send-push-notification.yml` | ✅ Auto-notify action ready |
| `send-notification.js` | ✅ Node.js sender ready |

---

## 🚀 3 Steps to Go Live

### Step 1 — Add GitHub Secret (2 min)
1. Go to: **GitHub Repo → Settings → Secrets → Actions → New Repository Secret**
2. Name: `FIREBASE_SERVICE_ACCOUNT_JSON`
3. Value: Paste the **full content** of your `serviceAccountKey.json` file
4. Click **Add Secret**

> ⚠️ Never commit serviceAccountKey.json to your repo

### Step 2 — Deploy Files (1 min)
Push all files to your GitHub repo main branch.
Netlify/Cloudflare Pages will auto-deploy.

### Step 3 — Test (2 min)
1. Open your site in browser
2. Open browser DevTools Console
3. Run: `TSJPush.testNotification('latest-jobs')`
4. → You should see a test notification!

---

## 📤 How to Send Notifications Manually

### Option A: GitHub Actions UI (No code needed)
1. GitHub Repo → **Actions** → "Send Push Notifications"
2. Click **Run Workflow**
3. Select category, enter title + body → **Run**

### Option B: Node.js on your PC
```bash
# Place serviceAccountKey.json in same folder
node send-notification.js
# Edit the sendToTopic() call at bottom of file
```

### Option C: Firebase Console
1. Firebase Console → **Messaging** → New Campaign
2. Title, Body → Target: **Topic** → `tsj-latest-jobs`
3. Schedule: Now → Publish

---

## 📋 Notification Categories

| Category Key | Topic | URL |
|---|---|---|
| `latest-jobs` | `tsj-latest-jobs` | /section/latest-jobs/ |
| `result` | `tsj-result` | /section/results/ |
| `admit-card` | `tsj-admit-card` | /section/admit-card/ |
| `admission` | `tsj-admission` | /section/admission/ |
| `answer-key` | `tsj-answer-key` | /section/answer-key/ |

---

## 🐛 Quick Troubleshooting

| Problem | Fix |
|---------|-----|
| No prompt shown | Wait 30 sec on site, or call `TSJPush.showPrompt()` in console |
| Permission denied | Browser Settings → Notifications → Allow topsarkarijobs.com |
| Token is null | Check VAPID key in tsj-push.js matches Firebase Console |
| GitHub Action fails | Check FIREBASE_SERVICE_ACCOUNT_JSON secret is set |
