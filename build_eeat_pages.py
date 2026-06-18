#!/usr/bin/env python3
"""PHASE 11: generate E-E-A-T trust pages (editorial / fact-check / correction /
source / author policy) using the existing disclaimer page as the head/footer
template, so styling + header/footer injection stay identical to the rest of the
site. 100% original content, honest aggregator framing."""
import re
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, 'disclaimer', 'index.html')
BASE = 'https://www.topsarkarijobs.com'
TODAY = '17 June 2026'


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


# (slug, title, meta_desc, H1, [(h2, paragraph_html), ...])
PAGES = [
    ('editorial-policy',
     'Editorial Policy – Top Sarkari Jobs',
     'How Top Sarkari Jobs sources, writes, reviews and updates government job information. Independent aggregator, not a government site.',
     'Editorial Policy',
     [
         ('Our Editorial Mission',
          'Top Sarkari Jobs exists to make official government recruitment information easier to find and understand. Our editorial goal is accuracy and clarity: we summarise official notifications faithfully and link back to the original source so readers can always verify the details themselves.'),
         ('How We Source Information',
          'Every job, result, admit card and admission listing on this site is based on a publicly available official notification or an official department/board website. We do not publish rumours, unverified leaks, or paid placements as news. Where a detail is unclear in the source, we either omit it or mark it as to be confirmed rather than guess.'),
         ('How Content Is Written and Reviewed',
          'Listings are prepared from the official notification, then checked against the source for key facts — post names, vacancy counts, eligibility, important dates and official links. We aim to use plain language and a consistent structure so readers can scan quickly. Headlines reflect the actual notification and are not written to mislead.'),
         ('Updates and Freshness',
          'Government information changes — dates get extended, corrigenda are issued, and results are declared in phases. We update listings as new official information becomes available, and we encourage readers to confirm the latest position on the official portal before acting.'),
         ('Independence',
          'Top Sarkari Jobs is an independent information portal. It is not a government website and is not affiliated with any government body. Our editorial decisions are not influenced by any government department or third party.'),
     ]),
    ('fact-check-policy',
     'Fact-Checking Policy – Top Sarkari Jobs',
     'How Top Sarkari Jobs verifies government job details against official sources before publishing. Always verify on the official portal.',
     'Fact-Checking Policy',
     [
         ('Why We Fact-Check',
          'Recruitment decisions are time-sensitive and high-stakes for candidates. An incorrect date or eligibility detail can cost someone an opportunity, so verifying against the official source is central to how we work.'),
         ('What We Verify',
          'Before publishing a listing we check the core facts against the official notification: the recruiting organisation, post names, total vacancies, eligibility and age criteria, application start and last dates, application fee, and the official application or notification link.'),
         ('Our Sources',
          'Our primary sources are official government notification PDFs and official department, commission, board and university websites. When we reference an external notification, we link to it so readers can confirm the original.'),
         ('Handling Uncertainty',
          'If a detail cannot be confirmed from the official source, we do not invent it. We either leave it out or clearly indicate that it is yet to be confirmed, and we advise readers to check the official portal.'),
         ('Reader Verification',
          'We always recommend that candidates read the full official notification and verify all details on the official website before applying or paying any fee. Our listing is a convenience summary, not a substitute for the official document.'),
     ]),
    ('correction-policy',
     'Correction Policy – Top Sarkari Jobs',
     'How to report an error on Top Sarkari Jobs and how we correct mistakes. We fix confirmed errors promptly and transparently.',
     'Correction Policy',
     [
         ('We Welcome Corrections',
          'Despite careful checking, errors can occur — a mistyped date, an outdated link, or a detail that changed after publishing. We take corrections seriously and fix confirmed errors as quickly as we can.'),
         ('How to Report an Error',
          'If you spot an error on any page, please email us at <a href="mailto:Topsarkarijobs.com@gmail.com" style="color:#1a56db;">Topsarkarijobs.com@gmail.com</a> with the page link and a short description of the issue. Including a link to the official source helps us verify and fix it faster.'),
         ('How We Handle Corrections',
          'We verify the reported issue against the official source. If the error is confirmed, we update the page promptly. Where a change is significant — for example a corrected last date — we aim to reflect the official position as soon as possible.'),
         ('Removing or Updating Outdated Listings',
          'When a recruitment closes or a notification is withdrawn by the issuing authority, we update or retire the relevant listing. If you believe a page contains outdated or withdrawn information, let us know and we will review it.'),
         ('Our Commitment',
          'Accuracy matters more than speed. If we cannot confirm a correction from an official source, we will not make a change that could mislead readers, and we will say so.'),
     ]),
]


def build_page(template_html, slug, title, meta_desc, h1, sections):
    head = template_html[:template_html.find('<main')]
    tail = template_html[template_html.find('</main>') + len('</main>'):]
    # fix head metadata
    head = re.sub(r'<title>[^<]*</title>', f'<title>{esc(title)}</title>', head, count=1)
    head = re.sub(r'(rel="canonical"[^>]*href=")[^"]*(")',
                  rf'\g<1>{BASE}/{slug}/\g<2>', head, count=1)
    if 'name="description"' in head:
        head = re.sub(r'(<meta name="description" content=")[^"]*(")',
                      rf'\g<1>{esc(meta_desc)}\g<2>', head, count=1)
    head = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                  rf'\g<1>{esc(title)}\g<2>', head, count=1)
    head = re.sub(r'(<meta name="twitter:title" content=")[^"]*(")',
                  rf'\g<1>{esc(title)}\g<2>', head, count=1)
    head = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                  rf'\g<1>{esc(meta_desc)}\g<2>', head, count=1)
    # fix the static <header><h1> leftover (template has one)
    head = re.sub(r'(<header>\s*<div class="container">\s*<h1>)[^<]*(</h1>)',
                  rf'\g<1>{esc(h1)}\g<2>', head, count=1)

    body_parts = [f'<main id="main-content" class="container">',
                  f'<h2 style="font-size:1.4rem;font-weight:800;color:#0d2257;margin:8px 0 14px;">{esc(h1)}</h2>']
    for h2, para in sections:
        body_parts.append(f'<h2>{esc(h2)}</h2>')
        body_parts.append(f'<p>{para}</p>')  # para may contain safe anchor html
    # related cross-links
    body_parts.append(
        '<div class="related-pages" style="margin-top:22px;padding-top:14px;'
        'border-top:1px solid #e2e8f0;font-size:.82rem;">'
        '<strong>Related:</strong> '
        '<a href="/about/" style="color:#1a56db;">About</a> &middot; '
        '<a href="/editorial-policy/" style="color:#1a56db;">Editorial Policy</a> &middot; '
        '<a href="/fact-check-policy/" style="color:#1a56db;">Fact-Checking Policy</a> &middot; '
        '<a href="/correction-policy/" style="color:#1a56db;">Correction Policy</a> &middot; '
        '<a href="/disclaimer/" style="color:#1a56db;">Disclaimer</a>'
        '</div>')
    body_parts.append('</main>')

    schema = (
        '<script type="application/ld+json">{'
        '"@context":"https://schema.org","@type":"WebPage",'
        f'"@id":"{BASE}/{slug}/#webpage","url":"{BASE}/{slug}/",'
        f'"name":"{esc(title)}","description":"{esc(meta_desc)}",'
        '"inLanguage":"en-IN","dateModified":"2026-06-17",'
        f'"isPartOf":{{"@id":"{BASE}/#website"}},'
        f'"publisher":{{"@id":"{BASE}/#organization"}}}}'
        '</script>')

    return head + ''.join(body_parts) + schema + tail


def main():
    template_html = open(TEMPLATE, encoding='utf-8').read()
    for slug, title, meta_desc, h1, sections in PAGES:
        out_dir = os.path.join(ROOT, slug)
        os.makedirs(out_dir, exist_ok=True)
        html = build_page(template_html, slug, title, meta_desc, h1, sections)
        open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8').write(html)
        wc = len(re.sub(r'<[^>]+>', ' ', ''.join(p for _, p in sections)).split())
        print(f"  /{slug}/ written ({wc} words)")


if __name__ == '__main__':
    main()
