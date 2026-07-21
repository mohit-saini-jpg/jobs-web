// TSJ AI — chat proxy (Vercel Edge Function)
//
// Keeps GROQ_API_KEY and TAVILY_API_KEY server-side only. The floating widget
// (tsj-chat.js) never talks to Groq/Tavily directly — a key embedded in
// client JS would be visible to anyone via DevTools and get scraped/abused
// within hours on a public site. This is the only piece of the assistant
// that isn't a static file.
//
// Required Vercel env vars (Project Settings -> Environment Variables):
//   GROQ_API_KEY    — free key from https://console.groq.com/keys
//   TAVILY_API_KEY  — free key from https://tavily.com (1000 searches/month
//                     free tier) — optional; without it the assistant still
//                     works, it just skips the live-web-search fallback and
//                     answers from the model's own knowledge instead.

export const config = { runtime: 'edge' };

// Tried in order; a model that's decommissioned/rate-limited/down just
// falls through to the next one. Update this list from
// https://console.groq.com/docs/models if Groq deprecates one of these.
const MODEL_FALLBACK_CHAIN = [
  'llama-3.3-70b-versatile',
  'openai/gpt-oss-120b',
  'llama-3.1-8b-instant',
  'openai/gpt-oss-20b',
];

const SYSTEM_PROMPT = `You are TSJ AI, the smart government job assistant built into TopSarkariJobs.com (topsarkarijobs.com) — an Indian government job/Sarkari Naukri portal that also hosts government schemes, useful official links/PDFs, and free online tools (photo/PDF/video utilities).

Answer ONLY government-job-related questions: recruitment notifications, vacancies, eligibility, exam patterns, syllabus, admit cards, results, answer keys, admissions, government schemes, state/district job listings, and how to use the site's own tools (resize photo, compress PDF, background remover, etc). If asked something completely unrelated (general chit-chat, coding help, etc.), politely redirect: tell the user you're focused on government jobs and TopSarkariJobs.com tools.

TOP-PRIORITY RULE — SITE CITATION MUST COME FIRST:
If "RELEVANT TOPSARKARIJOBS.COM CONTENT" is provided below and at least one entry genuinely matches the user's question, your reply MUST **begin** with that entry (or entries) — its Title as a Markdown link to its exact URL — before any explanation, summary, or other content. Do not bury it mid-answer or at the end. Any web-search / external links come strictly AFTER the site citation(s), clearly secondary. Format the opening like:
📌 **[Exact Title](https://www.topsarkarijobs.com/...)**
(then your explanation/details below it)
If the user's query matches MULTIPLE relevant entries (e.g. a profile-based "which jobs am I eligible for" question), list ALL of them at the top as a bulleted list of title+link, most recent first — not just one.
Only skip this opening citation if genuinely nothing in the provided site content matches the question — then say plainly this isn't listed on the site right now, and answer from web results / general knowledge instead.

Other rules:
- Entries below came from the site's own search index (fuzzy match, profile filter, or direct listing) — use judgment on whether each one actually answers the question; a "match confidence" score is given for fuzzy results (below ~0.3 = strong, above ~0.6 = weak guess, may not be relevant).
- Each entry has a type: Job posting, Govt Scheme, Official Link, PDF Download, Today Update, Education Update, Tool, Section (category hub page), State jobs hub, or District jobs hub — describe it appropriately (e.g. don't call a scheme a "job").
- If "USER PROFILE FILTER" is provided, the site-content list below was already filtered by the user's stated age/qualification — present it as "Aapki profile (qualification/age) ke hisaab se ye jobs mil sakti hain" (or English equivalent) followed by the full list; do not re-filter or second-guess it, and do not just pick one.
- If "LIVE WEB SEARCH RESULTS" is provided, use them only for information not found on the site, and only cite official sources (.gov.in, .nic.in, state government sites, official recruitment boards) — never unofficial job-aggregator blogs. Say "This information is based on official recruitment sources" when relying on these, and place them after any site citations.
- If neither site content nor web results are provided and you're answering from your own training knowledge, say so plainly (e.g. "Based on general information — please verify on the official website before applying") rather than presenting it as live/confirmed data.
- Never just say "I don't know" — give the most useful answer you can (general eligibility patterns for that type of exam, how to check officially, etc.) and be upfront about the uncertainty.
- Reply in the same language style the user used (Hindi, English, or Hinglish/Roman Hindi) — match them naturally.
- Format with Markdown: use headings/bold for job name/organization/vacancy/qualification/age limit/salary/selection process/important dates/how to apply where relevant, and keep tables simple.
- Be concise. Do not pad with generic disclaimers beyond what's asked.`;

const TYPE_LABELS = {
  job: 'Job posting', education: 'Education Update', scheme: 'Govt Scheme',
  link: 'Official Link', pdf: 'PDF Download', update: 'Today Update',
  tool: 'Tool', section: 'Section (category hub)', state: 'State jobs hub',
  district: 'District jobs hub',
};

function jsonError(message, status) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export default async function handler(request) {
  if (request.method !== 'POST') {
    return jsonError('Method not allowed', 405);
  }

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return jsonError('Invalid JSON body', 400);
  }

  const messages = Array.isArray(body.messages) ? body.messages : null;
  if (!messages || messages.length === 0) {
    return jsonError('messages[] is required', 400);
  }
  if (messages.length > 30) {
    return jsonError('Conversation too long — please start a new chat.', 400);
  }
  for (const m of messages) {
    if (!m || typeof m.content !== 'string' || (m.role !== 'user' && m.role !== 'assistant')) {
      return jsonError('Malformed message in conversation', 400);
    }
    if (m.content.length > 4000) {
      return jsonError('A message is too long (max 4000 characters).', 400);
    }
  }

  const lastUser = [...messages].reverse().find(m => m.role === 'user');
  const lastQuery = (lastUser && lastUser.content || '').slice(0, 500);

  let context = '';

  // Site data the widget already found via its own local search — local
  // fuzzy match, a profile-based (age/qualification) filter, or a direct
  // tool-keyword hit (see tsj-chat.js) — passed in so this function never
  // has to fetch/parse the site's large data files itself.
  const profileQuery = body.profileQuery && typeof body.profileQuery === 'object' ? body.profileQuery : null;
  const maxMatches = profileQuery ? 20 : 8;
  const siteMatches = Array.isArray(body.siteMatches) ? body.siteMatches.slice(0, maxMatches) : [];
  if (siteMatches.length) {
    if (profileQuery) {
      const age = Number.isFinite(profileQuery.age) ? `age ${profileQuery.age}` : '';
      context += `\n\nUSER PROFILE FILTER: ${[age, 'qualification-matched'].filter(Boolean).join(', ')} — the list below is every matching job on the site, already filtered. List ALL of them.\n`;
    }
    context += '\n\nRELEVANT TOPSARKARIJOBS.COM CONTENT (site\'s own search index; cite these FIRST per the top-priority rule):\n';
    for (const m of siteMatches) {
      if (!m || typeof m !== 'object') continue;
      const title = String(m.title || '').slice(0, 160);
      const org = String(m.org || '').slice(0, 100);
      const cat = String(m.category || '').slice(0, 60);
      const date = String(m.date || '').slice(0, 20);
      const url = String(m.url || '').slice(0, 200);
      const type = TYPE_LABELS[m.type] || 'Job posting';
      const conf = typeof m.score === 'number' ? ` | match confidence: ${m.score.toFixed(2)}` : '';
      if (!title) continue;
      const isAbsolute = /^https?:\/\//i.test(url);
      const fullUrl = isAbsolute ? url : `https://www.topsarkarijobs.com${url}`;
      context += `- [${type}] ${title}${org ? ' | ' + org : ''}${cat ? ' | ' + cat : ''}${date ? ' | Last date: ' + date : ''}${conf} | ${fullUrl}\n`;
    }
  }

  // Live official-source web search — only when the widget signals the site
  // data wasn't a good enough match, and only if a Tavily key is configured.
  if (body.needsWebSearch && process.env.TAVILY_API_KEY && lastQuery) {
    try {
      const tavilyRes = await fetch('https://api.tavily.com/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: process.env.TAVILY_API_KEY,
          query: `${lastQuery} government job India official notification`,
          search_depth: 'basic',
          max_results: 5,
        }),
      });
      if (tavilyRes.ok) {
        const data = await tavilyRes.json();
        const results = Array.isArray(data.results) ? data.results : [];
        if (results.length) {
          context += '\n\nLIVE WEB SEARCH RESULTS:\n';
          for (const r of results) {
            context += `- ${String(r.title || '').slice(0, 160)} — ${r.url}\n  ${String(r.content || '').slice(0, 280)}\n`;
          }
        }
      }
    } catch (e) {
      // best-effort only — chat still works without live search
    }
  }

  if (!process.env.GROQ_API_KEY) {
    return jsonError('AI is not configured yet (missing GROQ_API_KEY).', 500);
  }

  const groqMessages = [
    { role: 'system', content: SYSTEM_PROMPT + context },
    ...messages.slice(-20).map(m => ({ role: m.role, content: m.content })),
  ];

  let lastErr = '';
  for (const model of MODEL_FALLBACK_CHAIN) {
    try {
      const groqRes = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.GROQ_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model,
          messages: groqMessages,
          stream: true,
          temperature: 0.4,
          max_tokens: 1600,
        }),
      });
      if (!groqRes.ok || !groqRes.body) {
        lastErr = `${model}: HTTP ${groqRes.status}`;
        continue;
      }
      return new Response(groqRes.body, {
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream; charset=utf-8',
          'Cache-Control': 'no-cache, no-transform',
          'X-TSJ-Model': model,
        },
      });
    } catch (e) {
      lastErr = `${model}: ${String(e).slice(0, 100)}`;
    }
  }

  return jsonError(`All AI models are temporarily unavailable. Please try again shortly. (${lastErr})`, 503);
}
