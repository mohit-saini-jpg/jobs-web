// Dynamic per-page Open Graph share image (Vercel Edge Function + @vercel/og).
//
// WHY THIS EXISTS: before this, every page's og:image pointed at one of only
// 5 static PNGs bucketed by page "intent" (og-jobs.png / og-results.png /
// og-admit.png / og-scheme.png / og-study.png) — so a Police/Defence section
// page and a completely different UPPSC PCS job page both fell into the same
// "jobs" bucket and showed the IDENTICAL generic "Latest Sarkari Jobs 2026"
// card on WhatsApp/Telegram. This route renders a fresh 1200x630 image per
// request from ?title=/?tag=/?type=, so every URL's share preview reflects
// its own actual title — a job page shows its own job title, a section page
// shows its own section name, a tool shows its own tool name, etc.
//
// No JSX (this repo has no bundler/Babel config) — the element tree is built
// by hand with the h() helper below, which produces the same
// {type, props:{style, children}} shape Satori (the renderer @vercel/og
// wraps) expects from JSX. Every node needs an explicit display (Satori has
// no default block layout, flex-only).
//
// Fonts: Noto Sans Devanagari (SIL OFL, free) bundled under fonts/og/ so job
// titles that are partly/fully in Hindi render correctly — the free Google
// Fonts variant also covers the Latin glyphs used in the English/brand text.

export const config = { runtime: 'edge' };

import { ImageResponse } from '@vercel/og';

function h(type, props, ...children) {
  const flat = children.flat(Infinity).filter((c) => c !== null && c !== undefined && c !== false);
  return { type, props: { ...(props || {}), children: flat.length === 1 ? flat[0] : flat } };
}

const TYPE_THEME = {
  jobs:    { grad: ['#0b1f4d', '#1d3fa0'], badge: 'GOVT JOBS',      tagline: 'Apply Online — Eligibility, Dates & Notification' },
  results: { grad: ['#052e2b', '#0f766e'], badge: 'RESULT OUT',     tagline: 'Check Your Result — Direct Download Link' },
  admit:   { grad: ['#2e1065', '#6d28d9'], badge: 'ADMIT CARD',     tagline: 'Download Admit Card — Exam Date & Center' },
  scheme:  { grad: ['#062e1f', '#059669'], badge: 'GOVT SCHEME',    tagline: 'Government Scheme — Eligibility & Apply Online' },
  study:   { grad: ['#1e1b4b', '#4338ca'], badge: 'STUDY MATERIAL', tagline: 'Syllabus · Notes · Previous Papers · Mock Tests' },
  tool:    { grad: ['#0f172a', '#0d9488'], badge: 'FREE TOOL',      tagline: '100% Free — No Signup Required' },
};

function trim(s, max) {
  s = (s || '').toString().trim();
  if (s.length <= max) return s;
  return s.slice(0, max - 1).trim() + '…';
}

// Satori (the layout engine @vercel/og wraps) doesn't run Devanagari's
// pre-base reordering: Unicode stores VOWEL SIGN I (ि, U+093F) AFTER its
// base consonant but it must be drawn BEFORE it ("पुलिस" not "पुलसि"). A real
// text shaper (HarfBuzz) does this automatically; Satori draws glyphs in
// plain logical order, so titles like "...पुलिस भर्ती..." rendered with the
// mark on the wrong side. Fix: move ि (and its consonant/conjunct cluster)
// in the STRING itself before handing text to Satori — confirmed by local
// render test to produce correct output.
function reorderDevanagariMatra(s) {
  return (s || '').replace(/((?:[क-हक़-य़]्)*[क-हक़-य़])ि/g, 'ि$1');
}

export default async function handler(req) {
  const { searchParams } = new URL(req.url);
  const title = reorderDevanagariMatra(trim(searchParams.get('title') || 'Top Sarkari Jobs', 78));
  const tag = reorderDevanagariMatra(trim(searchParams.get('tag') || '', 60));
  const typeKey = (searchParams.get('type') || 'jobs').toLowerCase();
  const theme = TYPE_THEME[typeKey] || TYPE_THEME.jobs;
  const year = new Date().getFullYear();
  const headlineSize = title.length > 55 ? 46 : title.length > 34 ? 54 : 64;

  const [regular, bold] = await Promise.all([
    fetch(new URL('../fonts/og/NotoSansDevanagari-Regular.ttf', import.meta.url)).then((r) => r.arrayBuffer()),
    fetch(new URL('../fonts/og/NotoSansDevanagari-Bold.ttf', import.meta.url)).then((r) => r.arrayBuffer()),
  ]);

  const tree = h(
    'div',
    { style: { height: '100%', width: '100%', display: 'flex', flexDirection: 'column', background: `linear-gradient(135deg, ${theme.grad[0]}, ${theme.grad[1]})` } },
    h(
      'div',
      { style: { display: 'flex', flexDirection: 'column', flex: 1, padding: '54px 64px 10px' } },
      h('div', { style: { display: 'flex', alignItems: 'center' } },
        h('div', { style: { display: 'flex', background: '#f59e0b', color: '#1e1b0a', fontWeight: 700, fontSize: 22, padding: '6px 20px', borderRadius: 8 } }, String(year))
      ),
      h('div', { style: { display: 'flex', flexDirection: 'column', marginTop: 20 } },
        h('div', { style: { display: 'flex', color: '#fff', fontSize: 28, fontWeight: 700, letterSpacing: 1 } }, 'TOP SARKARI JOBS'),
        h('div', { style: { display: 'flex', color: 'rgba(255,255,255,.7)', fontSize: 18, marginTop: 2 } }, 'topsarkarijobs.com')
      ),
      h('div', { style: { display: 'flex', flex: 1, alignItems: 'center' } },
        h('div', { style: { display: 'flex', color: '#fff', fontSize: headlineSize, fontWeight: 700, lineHeight: 1.2 } }, title)
      ),
      h('div', { style: { display: 'flex', flexDirection: 'column' } },
        tag ? h('div', { style: { display: 'flex', color: 'rgba(255,255,255,.85)', fontSize: 24, fontWeight: 400, marginBottom: 14 } }, tag) : null,
        h('div', { style: { display: 'flex', color: 'rgba(255,255,255,.75)', fontSize: 22, fontWeight: 400, marginBottom: 18 } }, theme.tagline),
        h('div', { style: { display: 'flex', gap: 12 } },
          h('div', { style: { display: 'flex', background: 'rgba(255,255,255,.14)', border: '1.5px solid rgba(255,255,255,.32)', borderRadius: 999, padding: '8px 22px', color: '#fff', fontSize: 20, fontWeight: 700 } }, theme.badge),
          h('div', { style: { display: 'flex', background: 'rgba(255,255,255,.14)', border: '1.5px solid rgba(255,255,255,.32)', borderRadius: 999, padding: '8px 22px', color: '#fff', fontSize: 20, fontWeight: 700 } }, 'ALL INDIA')
        )
      )
    ),
    h('div', { style: { display: 'flex', background: '#f59e0b', padding: '18px 64px', alignItems: 'center' } },
      h('div', { style: { display: 'flex', color: '#1e1b0a', fontWeight: 700, fontSize: 22 } }, "India's No.1 Sarkari Jobs Portal | topsarkarijobs.com")
    )
  );

  return new ImageResponse(tree, {
    width: 1200,
    height: 630,
    fonts: [
      { name: 'Noto Sans Devanagari', data: regular, weight: 400, style: 'normal' },
      { name: 'Noto Sans Devanagari', data: bold, weight: 700, style: 'normal' },
    ],
    headers: {
      'Cache-Control': 'public, max-age=86400, s-maxage=31536000, immutable',
    },
  });
}
