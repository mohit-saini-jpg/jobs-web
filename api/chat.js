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

const SYSTEM_PROMPT = `You are TSJ AI, the smart government job assistant built into TopSarkariJobs.com (topsarkarijobs.com) — an Indian government job/Sarkari Naukri portal.

Answer ONLY government-job-related questions: recruitment notifications, vacancies, eligibility, exam patterns, syllabus, admit cards, results, answer keys, admissions, government schemes, and how to use the site's own tools (resize photo, compress PDF, background remover, etc). If asked something completely unrelated (general chit-chat, coding help, etc.), politely redirect: tell the user you're focused on government jobs and TopSarkariJobs.com tools.

Rules:
- If "RELEVANT TOPSARKARIJOBS.COM DATA" is provided below, it came from a fuzzy search over the site's real listings, so it may include near-misses or nothing useful at all — use your judgment on whether each entry actually answers the user's question. For any entry that does genuinely match: you MUST prefer it over general/web knowledge, and you MUST include its exact URL (formatted as a Markdown link, e.g. "[Haryana Anganwadi Recruitment 2026](https://www.topsarkarijobs.com/jobs/...)") directly in your answer — never describe a real site listing without linking to it. If none of the entries actually match the question, ignore them and say this specific posting isn't listed on the site right now, then answer from web results / general knowledge instead.
- If "LIVE WEB SEARCH RESULTS" is provided, you may use them for information not on the site, but only cite official sources (.gov.in, .nic.in, state government sites, official recruitment boards) — never unofficial job-aggregator blogs. Say "This information is based on official recruitment sources" when you rely on these.
- If neither is provided and you're answering from your own training knowledge, say so plainly (e.g. "Based on general information — please verify on the official website before applying") rather than presenting it as live/confirmed data.
- Never just say "I don't know" — give the most useful answer you can (general eligibility patterns for that type of exam, how to check officially, etc.) and be upfront about the uncertainty.
- Reply in the same language style the user used (Hindi, English, or Hinglish/Roman Hindi) — match them naturally.
- Format with Markdown: use headings/bold for job name/organization/vacancy/qualification/age limit/salary/selection process/important dates/how to apply where relevant, and keep tables simple.
- Be concise. Do not pad with generic disclaimers beyond what's asked.`;

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

  // Site data the widget already found via its own local fuzzy search
  // (see tsj-chat.js) — passed in so this function never has to fetch/parse
  // the site's large data files itself.
  const siteMatches = Array.isArray(body.siteMatches) ? body.siteMatches.slice(0, 8) : [];
  if (siteMatches.length) {
    context += '\n\nRELEVANT TOPSARKARIJOBS.COM DATA (from fuzzy search — a "match confidence" is given for each; below ~0.3 is a strong match, above ~0.6 is a weak guess and may not actually be what the user asked about):\n';
    for (const m of siteMatches) {
      if (!m || typeof m !== 'object') continue;
      const title = String(m.title || '').slice(0, 160);
      const org = String(m.org || '').slice(0, 100);
      const cat = String(m.category || '').slice(0, 60);
      const date = String(m.date || '').slice(0, 20);
      const url = String(m.url || '').slice(0, 200);
      const conf = typeof m.score === 'number' ? ` | match confidence: ${m.score.toFixed(2)}` : '';
      if (!title) continue;
      context += `- ${title}${org ? ' | ' + org : ''}${cat ? ' | ' + cat : ''}${date ? ' | Last date: ' + date : ''}${conf} | https://www.topsarkarijobs.com${url}\n`;
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
