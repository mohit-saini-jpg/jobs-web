# 🔄 Cache Auto-Clear Guide — Top Sarkari Jobs

## Jab bhi koi file update karo — yeh 2 kaam karo:

### Step 1: sw.js mein BUILD_VERSION badlo
File: `sw.js` — line 11
```
const BUILD_VERSION = '20260516-1200';  ← Yahan date+time update karo
```
Example: `'20260520-0900'` (20 May, 9 AM)

### Step 2: index.html mein SW register line update karo  
File: `index.html` — SW registration script mein:
```html
navigator.serviceWorker.register('/sw.js?v=20260516')
```
Yahan bhi same date daal do.

---

## Kaise kaam karta hai?

1. Aap `BUILD_VERSION` change karte ho
2. Browser detect karta hai ki `sw.js` file badli hai (`?v=` query se)
3. Naya SW install hota hai background mein
4. Purana cache automatically delete hota hai
5. User ko fresh content milta hai — **page reload bhi nahi chahiye!**

---

## Script aur CSS files ke liye (already set hai):
`script.js?v=20260508` — yahan bhi version badlo jab script update karo

---

## Emergency: Abhi turant cache clear karna ho
Browser console mein run karo:
```javascript
navigator.serviceWorker.controller.postMessage({type: 'CLEAR_CACHE'});
location.reload();
```
