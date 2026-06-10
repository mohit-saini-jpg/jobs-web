# WHERE TO PUT FILES — Complete Site (Final) 2026-06-10

Repo: `mohit-saini-jpg/jobs-web` | Branch: `main`

Yeh **complete site ZIP** hai. Extract karke poora content repo me replace
karke push kar do. Netlify auto-deploy. UI/design/layout/CSS kuch nahi badla.

---

## Is build me kya hai

### ✅ Listing pages — pehle jaise (kuch nahi toda)
- Ek job apni **saari relevant categories** ki list me dikhta hai
  (10th Pass = 62, Latest Jobs, B.Tech, state-wise, education — sab intact).
- **JSON order preserved**: jo item JSON me pehle, woh listing me upar; purane
  neeche.
- Listing ka har job link uske **single canonical `/jobs/{slug}/` page** pe
  jaata hai.
- **0 broken internal links** (verified).
- Detail page complete data ke saath (Dates, Vacancy, Eligibility, Fee,
  How to Apply, Links, Age Limit, FAQ) — pehle jaisa.

### ✅ One Job = One URL = One HTML page
Generator ab ek recruitment ke liye **sirf ek** detail page banata hai. Pehle
har qualification category ke liye alag duplicate page (`-bba`, `-bca`,
`-mba-pgdm`...) banta tha — woh band. Aage naye duplicate **nahi** banenge.
Dono generator copies fixed + synced:
- `/generate_all.py`
- `/.github/workflows/generate_all.py`

### ✅ Homepage single URL
`/index.html` → `/` 301 redirect. Sirf `https://www.topsarkarijobs.com/`.

### ✅ www canonical (already tha — verified)
non-www / http sab `https://www.` pe 301.

---

## NOTE — purane duplicate pages
Aapke pehle live site pe jo `-bba`/`-bca`/`-latest-jobs` type purane duplicate
pages the, woh is build me **delete nahi** kiye gaye (taaki koi 404 na aaye aur
listing kuch na tute). Generator unhe dobara nahi banata, par delete bhi nahi
karta. Jab aap ready ho, in purane duplicates ko canonical-redirect se master
page pe consolidate karwa sakte ho — woh alag se safe step me kar dunga.

---

## Deploy ke baad (GSC)
1. `https://www.topsarkarijobs.com/index.html` kholo → `/` pe redirect ho.
2. GSC → Sitemaps → `sitemap-index.xml` dobara submit (refresh).
3. Indexing kuch hafton me improve hoga.
