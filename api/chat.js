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

// LLMs reliably paraphrase/"clean up" URLs even when told to copy them
// verbatim (confirmed live: a real /district/ambala-haryana/ entry came back
// as a plausible-looking but fake /latest-jobs/ambala-jobs, a 404). Rather
// than trust the model to type a topsarkarijobs.com URL correctly, it's only
// ever allowed to reference one via a [[SITE:N]] index token, which this
// server resolves into the real, verbatim URL after the fact — the model
// physically cannot mistype a link this way.
const SYSTEM_PROMPT = `You are TSJ AI, the smart government job assistant built into TopSarkariJobs.com (topsarkarijobs.com) — an Indian government job/Sarkari Naukri portal that also hosts government schemes, useful official links/PDFs, and free online tools (photo/PDF/video utilities).

Answer ONLY government-job-related questions: recruitment notifications, vacancies, eligibility, exam patterns, syllabus, admit cards, results, answer keys, admissions, government schemes, state/district job listings, and how to use the site's own tools (resize photo, compress PDF, background remover, etc). If asked something completely unrelated (general chit-chat, coding help, etc.), politely redirect: tell the user you're focused on government jobs and TopSarkariJobs.com tools.

TOP-PRIORITY RULE — SITE CITATION MUST COME FIRST, AND MUST USE TOKENS:
If a "TOPSARKARIJOBS.COM CONTENT" list is provided below, each entry is numbered like "[0]", "[1]", etc. When you want to cite/link entry N, write the exact literal bare token [[SITE:N]] (with the real number) on its OWN line, with a blank line before and after it — never two tokens back to back on the same line, never inside a sentence, never wrapped in ** bold ** or other markdown, never followed immediately by more text or another token with no space. Do NOT write a Markdown link or type out any topsarkarijobs.com URL yourself, ever, for any reason, even if you're sure you remember it correctly — the token gets replaced with the real, correct, clickable link+title automatically after you respond, already nicely formatted; writing your own URL instead risks a broken/wrong link, which is strictly worse than using the token.
Your reply MUST **begin** with the [[SITE:N]] token(s) — each on its own line — for every entry that genuinely matches the user's question, before any explanation, summary, or other content — do not bury it mid-answer or at the end. If multiple entries match (e.g. a profile-based "which jobs am I eligible for" question, or a "USER PROFILE FILTER" list), open with ALL of them, one token per line, most recent first — not just one, and do not add your own bullet dash or numbering in front of a token, it already renders as its own block. After the last token, leave a blank line, then continue with your explanation/details in plain prose. Any web-search/external links come strictly AFTER the site token(s), clearly secondary.
Only skip the opening token if genuinely nothing in the provided list matches the question — then say plainly this isn't listed on the site right now, and answer from web results / general knowledge instead.

Other rules:
- Entries below came from the site's own search index (fuzzy match, profile filter, or direct listing) — use judgment on whether each one actually answers the question; a "match confidence" score is given for fuzzy results (below ~0.3 = strong, above ~0.6 = weak guess, may not be relevant). Only use the [[SITE:N]] token for entries that are genuinely relevant — skip weak/irrelevant ones entirely rather than tokening them "just in case".
- Each entry has a type: Job posting, Govt Scheme, Official Link, PDF Download, Today Update, Education Update, Tool, Section (category hub page), State jobs hub, or District jobs hub — describe it appropriately in your prose (e.g. don't call a scheme a "job"). A "Section (category hub)" entry is a browse-all page for that qualification/category — mention it as "poori list yahaan dekhein" alongside the individual job tokens, not instead of them.
- If "USER PROFILE FILTER" is provided, the list below was already filtered by the user's stated age/qualification — present it as "Aapki profile (qualification/age) ke hisaab se ye jobs mil sakti hain" (or English equivalent) followed by a [[SITE:N]] token, one per line, for every single entry in the list; do not re-filter, second-guess, skip any, or pick just one.
- If a "LIVE WEB SEARCH RESULTS" block is provided below, those are already restricted to official government (.gov.in/.nic.in/.ac.in) sources — wrap that whole part of your answer between literal marker lines [[WEBINFO]] and [[/WEBINFO]] (each marker alone on its own line), and inside it you may write those URLs directly (they are not topsarkarijobs.com links, so the token rule doesn't apply to them). Say "This information is based on official recruitment sources" when relying on these.
- If NO "LIVE WEB SEARCH RESULTS" block is provided below, that means no live search ran for this question — you MUST NOT write the phrase "live web search", "ke anusaar", or any specific number/statistic/website name as if it came from one. Never invent a website domain from memory (real or plausible-sounding — e.g. never write anything like "govtjobguru.in" or "rojgaradda.in" or "careerera.com" or ANY third-party job-portal domain) and never fabricate vacancy counts. Simply answer from general knowledge and say so plainly, or point the user to the official site of the department/exam by name (not a guessed URL).
- Never mention or link to any job-aggregator/portal/job-board site other than topsarkarijobs.com and official .gov.in/.nic.in/.ac.in sources — no LinkedIn, Naukri, Indeed, FreeJobAlert, SarkariResult, GovtJobsLive, or any other private jobs website, ever, under any circumstance, even one you recall from your own training knowledge and even if it seems helpful.
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

// A blocklist of competitor domains can never keep up with the long tail of
// job-aggregator sites (rojgaradda.in, careerera.com, govtjobguru.in, ... —
// confirmed live, none of these were on an earlier hand-picked blocklist).
// The only reliable fix is the opposite: an ALLOWLIST of official domain
// suffixes, checked against every Tavily result after the fact — anything
// not ending in one of these is dropped, whatever it is.
const OFFICIAL_SUFFIXES = ['.gov.in', '.nic.in', '.ac.in', '.edu.in', '.res.in', '.mil.in', '.org.in'];
function isOfficialUrl(url) {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return OFFICIAL_SUFFIXES.some(suf => host.endsWith(suf));
  } catch (e) {
    return false;
  }
}

function jsonError(message, status) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function siteUrl(m) {
  const url = String(m.url || '').slice(0, 200);
  return /^https?:\/\//i.test(url) ? url : `https://www.topsarkarijobs.com${url}`;
}

// Resolves [[SITE:N]] tokens into real Markdown links, and — since the
// model has been caught fabricating an entire "live search" complete with
// invented domain names (govtjobguru.in, rojgaradda.in, careerera.com —
// none of which were ever in its context) even after being told not to —
// strips out any link whose host isn't topsarkarijobs.com or one of the
// exact official URLs actually handed to it this turn. Buffers across SSE
// chunk boundaries so a token/link split mid-stream can't leak through
// unresolved or unfiltered.
function createTokenResolverStream(siteMatches, allowedExternalHosts) {
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  let sseBuf = '';
  let textBuf = '';

  function resolveSiteTokens(text) {
    // Forced blank-line isolation on every side: even when the model ignores
    // the "one token per line" instruction and runs several together with no
    // separator (confirmed live — multiple job titles got smashed into one
    // unreadable run-on paragraph), each citation still lands as its own
    // paragraph rather than merging into its neighbors.
    return text.replace(/\[\[SITE:(\d+)\]\]/g, (whole, idxStr) => {
      const m = siteMatches[parseInt(idxStr, 10)];
      if (!m) return '';
      const title = String(m.title || '').replace(/[[\]]/g, '').slice(0, 160);
      return `\n\n[${title}](${siteUrl(m)})\n\n`;
    });
  }

  function isAllowedHost(url) {
    try {
      const host = new URL(url).hostname.toLowerCase();
      if (host === 'topsarkarijobs.com' || host === 'www.topsarkarijobs.com') return true;
      return allowedExternalHosts.has(host);
    } catch (e) {
      return false;
    }
  }

  function looksLikeBareDomain(s) {
    return /^(https?:\/\/)?(www\.)?[a-z0-9-]+(\.[a-z0-9-]+)+\/?$/i.test(s.trim());
  }

  function stripDisallowedLinks(text) {
    // Markdown-style [text](url) — for a disallowed link, the label text
    // itself is often just the fake domain name again (confirmed live:
    // "[govtjobguru.in](https://govtjobguru.in)"), so de-linking alone still
    // leaves the fabricated domain readable; drop the label too when it's
    // nothing but a bare domain, keep it when it's genuine descriptive prose.
    text = text.replace(/\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g, (whole, label, url) => {
      if (isAllowedHost(url)) return whole;
      return looksLikeBareDomain(label) ? '' : label;
    });
    // Bare (non-markdown) URLs the model wrote directly in prose. Deliberately
    // NOT also stripping bare domain-like text with no URL scheme at all
    // (e.g. a lone "rojgaradda.in") — that pattern collides with legitimate
    // qualification abbreviations this same bot uses constantly ("B.Com",
    // "M.Com" both match a naive TLD-suffix regex) and hasn't been observed
    // in practice; the markdown-link case above is the one actually seen live.
    text = text.replace(/\bhttps?:\/\/[^\s)]+/g, (url) => (isAllowedHost(url) ? url : ''));
    return text;
  }

  // Find the earliest position near the tail that could still be growing
  // into a token, markdown link, or bare URL — everything before it is safe
  // to emit now. Must take the EARLIEST risky position, not the latest: an
  // earlier bug used the latest of "[[", "[", "http", which let a URL's own
  // "http" (nested inside an already-fully-formed [label](url)) win over the
  // link's opening bracket — splitting the buffer mid-URL, so the link never
  // appeared whole in one resolve() call and a disallowed domain slipped
  // through unstripped (confirmed via a direct repro of the live bug).
  function findHoldBackIndex(text) {
    const candidates = [];
    const lastDouble = text.lastIndexOf('[[');
    if (lastDouble !== -1 && !/^\[\[SITE:\d+\]\]/.test(text.slice(lastDouble))) {
      candidates.push(lastDouble);
    }
    // Skip a "[" that's actually the second half of a "[[" pair (already
    // judged above) — evaluated on its own it looks like an incomplete
    // single-bracket link even when the real [[SITE:N]] token is complete,
    // which held back and fragmented an already-whole token across two
    // resolve() calls, so neither call ever saw the full "[[SITE:N]]" text.
    const lastSingle = text.lastIndexOf('[');
    if (lastSingle !== -1 && text[lastSingle - 1] !== '[') {
      const after = text.slice(lastSingle);
      const complete = /^\[\[SITE:\d+\]\]/.test(after) || /^\[[^\]]*\]\([^)]*\)/.test(after);
      if (!complete) candidates.push(lastSingle);
    }
    const lastHttp = text.lastIndexOf('http');
    if (lastHttp !== -1 && text[lastHttp - 1] !== '(') {
      if (!/[\s)]/.test(text.slice(lastHttp))) candidates.push(lastHttp);
    }
    return candidates.length ? Math.min(...candidates) : -1;
  }
  function splitSafe(text) {
    const idx = findHoldBackIndex(text);
    if (idx !== -1 && idx > text.length - 300) {
      return [text.slice(0, idx), text.slice(idx)];
    }
    return [text, ''];
  }

  function emitDelta(controller, content) {
    if (!content) return;
    controller.enqueue(encoder.encode(`data: ${JSON.stringify({ choices: [{ delta: { content } }] })}\n\n`));
  }

  return new TransformStream({
    transform(chunk, controller) {
      sseBuf += decoder.decode(chunk, { stream: true });
      const lines = sseBuf.split('\n');
      sseBuf = lines.pop();
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const data = trimmed.slice(5).trim();
        if (data === '[DONE]') continue; // emitted once at true stream end, in flush()
        let delta = '';
        try {
          const json = JSON.parse(data);
          delta = (json.choices && json.choices[0] && json.choices[0].delta && json.choices[0].delta.content) || '';
        } catch (e) { continue; }
        if (!delta) continue;
        textBuf += delta;
        const [safe, hold] = splitSafe(textBuf);
        textBuf = hold;
        emitDelta(controller, stripDisallowedLinks(resolveSiteTokens(safe)));
      }
    },
    flush(controller) {
      if (textBuf) emitDelta(controller, stripDisallowedLinks(resolveSiteTokens(textBuf)));
      controller.enqueue(encoder.encode('data: [DONE]\n\n'));
    },
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
  // has to fetch/parse the site's large data files itself. Numbered so the
  // model can reference each one by index via a [[SITE:N]] token instead of
  // ever writing out a topsarkarijobs.com URL itself.
  const profileQuery = body.profileQuery && typeof body.profileQuery === 'object' ? body.profileQuery : null;
  const maxMatches = profileQuery ? 20 : 8;
  const siteMatches = Array.isArray(body.siteMatches) ? body.siteMatches.slice(0, maxMatches) : [];
  if (siteMatches.length) {
    if (profileQuery) {
      const age = Number.isFinite(profileQuery.age) ? `age ${profileQuery.age}` : '';
      context += `\n\nUSER PROFILE FILTER: ${[age, 'qualification-matched'].filter(Boolean).join(', ')} — the list below is every matching job on the site, already filtered. Token ALL of them.\n`;
    }
    context += '\n\nTOPSARKARIJOBS.COM CONTENT (cite via [[SITE:N]] tokens ONLY — see top-priority rule):\n';
    siteMatches.forEach((m, i) => {
      if (!m || typeof m !== 'object') return;
      const title = String(m.title || '').slice(0, 160);
      if (!title) return;
      const org = String(m.org || '').slice(0, 100);
      const cat = String(m.category || '').slice(0, 60);
      const date = String(m.date || '').slice(0, 20);
      const type = TYPE_LABELS[m.type] || 'Job posting';
      const conf = typeof m.score === 'number' ? ` | match confidence: ${m.score.toFixed(2)}` : '';
      context += `[${i}] [${type}] ${title}${org ? ' | ' + org : ''}${cat ? ' | ' + cat : ''}${date ? ' | Last date: ' + date : ''}${conf}\n`;
    });
  }

  // Live official-source web search — only when the widget signals the site
  // data wasn't a good enough match, and only if a Tavily key is configured.
  // max_results is fetched generously since the strict allowlist filter
  // below throws most general-web results away. The surviving hosts become
  // the ONLY external domains the streamed reply is allowed to link to
  // (see createTokenResolverStream) — this is what actually stops a
  // fabricated domain from rendering as a link, not just the prompt asking
  // nicely, since the model has been caught inventing "live search" results
  // (specific fake stats and domain names) even when this block was empty.
  const allowedExternalHosts = new Set();
  if (body.needsWebSearch && process.env.TAVILY_API_KEY && lastQuery) {
    try {
      const tavilyRes = await fetch('https://api.tavily.com/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: process.env.TAVILY_API_KEY,
          query: `${lastQuery} government job India official notification`,
          search_depth: 'basic',
          max_results: 10,
        }),
      });
      if (tavilyRes.ok) {
        const data = await tavilyRes.json();
        const results = (Array.isArray(data.results) ? data.results : [])
          .filter(r => r && isOfficialUrl(r.url))
          .slice(0, 5);
        if (results.length) {
          context += '\n\nLIVE WEB SEARCH RESULTS (already restricted to official .gov.in/.nic.in/.ac.in sources):\n';
          for (const r of results) {
            context += `- ${String(r.title || '').slice(0, 160)} — ${r.url}\n  ${String(r.content || '').slice(0, 280)}\n`;
            try { allowedExternalHosts.add(new URL(r.url).hostname.toLowerCase()); } catch (e) {}
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
      const resolvedStream = groqRes.body.pipeThrough(createTokenResolverStream(siteMatches, allowedExternalHosts));
      return new Response(resolvedStream, {
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
