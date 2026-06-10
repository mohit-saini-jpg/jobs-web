# WHERE TO PUT FILES — Complete Clean Site 2026-06-10

Repo: `mohit-saini-jpg/jobs-web` | Branch: `main`

Extract karke poora content repo me replace karke push kar do. Netlify auto-deploy.
UI/design/layout/CSS kuch nahi badla.

## Final state (sab verified)
- **0 duplicate pages** — 656 true-duplicate HTML pages (`-bba`, `-bca`, `-latest-jobs`
  etc., jinka content master jaisa hi tha) delete kar diye. Har deleted URL ka **301
  redirect** master page pe (koi 404 nahi).
- **One page = One URL** — 3,200 unique job pages, har ek ka apna sahi self-canonical.
  Google ab ek recruitment ka ek hi page index karega.
- **Ek item, alag categories, same URL** — ek job apni saari qualifications ki list me
  dikhta hai (jaise IIM Bodh Gaya 15 categories me), par sab ek hi `/jobs/{slug}/` URL
  pe. Listing pehle jaisa intact (10th Pass = 62, etc.).
- **JSON order preserved** — JSON me jo pehle, listing me upar.
- **0 broken internal links** — 3 truncation-broken + 1 orphan link bhi theek kar diye.
- **Homepage single URL** — `/index.html` → `/` 301 (neeche detail).
- **Generator fixed (dono copies)** — aage naye duplicate nahi banenge.
- **Sitemap cleaned** — 656 dup URLs hate, 3,200 valid URLs, valid XML.

## NON-duplicate purane pages
Sirf TRUE duplicates (same content) delete hue. Jo purane pages unique content
rakhte the, woh sab safe hain — kuch nahi hata.

## Deploy ke baad (GSC)
1. `https://www.topsarkarijobs.com/index.html` → `/` redirect verify karo.
2. GSC → Sitemaps → `sitemap-index.xml` dobara submit.
3. Indexing kuch hafton me improve hoga.
