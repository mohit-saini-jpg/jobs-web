import json, re, os

print("Loading Complete_Jobs_Full_Data.json...")
with open('Complete_Jobs_Full_Data.json', encoding='utf-8') as f:
    data = json.load(f)

def slugify(text):
    text = str(text).lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text[:120].strip('-') or 'job'

# Path: jobs/data/
os.makedirs('jobs/data', exist_ok=True)

index = {}
count = 0

for cat, jobs in data.items():
    if not isinstance(jobs, list):
        continue
    for job in jobs:
        bd    = job.get('basic_details', {})
        dates = job.get('important_dates', {})
        title = bd.get('job_title', '').strip()
        if not title:
            continue

        slug      = slugify(title)
        last_date = dates.get('last_date', '')

        with open(f'jobs/data/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump(job, f, ensure_ascii=False, separators=(',', ':'))

        index[slug] = {
            'cat':       cat,
            'title':     title[:120],
            'last_date': last_date[:30] if last_date else ''
        }
        count += 1

with open('jobs-index.json', 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, separators=(',', ':'))

print(f"Done! {count} jobs processed.")
