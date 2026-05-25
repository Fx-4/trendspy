# TrendSpy — Claude Code Project Guide

## What is this?
TrendSpy is a real-time market intelligence tool for indie makers and startup founders.
User types a niche/idea → AI crawls Reddit + web → streams back a Market Intelligence Brief (pain points, competitor gaps, pricing signals, hot communities) in ~15-20 seconds via SSE.

Built for: **DeveloperWeek New York 2026 Hackathon** (Devpost)
Deadline: **June 10, 2026**
Developer: Solo

---

## Architecture

```
frontend/ (React + Vite)  →  Vercel (free)
backend/  (FastAPI)        →  Render.com free instance (always-on, no timeout)
database  (Supabase)       →  PostgreSQL + Auth + Storage
cache     (Upstash Redis)  →  Rate limiting & dedup
```

### Why FastAPI on Render (not Next.js on Vercel)?
- Vercel hobby plan serverless timeout = **10 seconds**. Analysis takes 15-30s → would always fail.
- Render free instance = **always-on**, no cold start, no timeout limit.
- FastAPI supports **SSE (Server-Sent Events)** natively via `StreamingResponse`.
- Python async is ideal for parallel API calls (`asyncio.gather`).

### Key UX Mechanic: SSE Streaming
The killer feature. Instead of a spinner for 20 seconds, user sees:
1. "🔍 Scanning Reddit... 23 posts found ✓" — appears at ~4s
2. "🌐 Web intelligence gathered ✓" — appears at ~7s
3. "🧠 AI analyzing 847 data points..." — appears at ~9s
4. Pain points stream in one by one via Groq token streaming — starts at ~12s
5. Sections complete progressively: gaps → pricing → communities → summary
6. "✅ Done! Save or Share" — appears at ~18-22s

---

## Tech Stack (100% Free, Verified)

| Layer | Tool | Free Limit | Notes |
|-------|------|-----------|-------|
| Frontend | React + Vite + Tailwind + shadcn/ui | Unlimited | |
| Hosting FE | Vercel | Unlimited hobby | |
| Backend | FastAPI (Python 3.11+) | Unlimited | |
| Hosting BE | Koyeb `free` instance | 512MB RAM, 0.1 vCPU | CC needed (no charge) |
| Database | Supabase PostgreSQL | 500MB | |
| Auth | Supabase Auth | 50K MAU | |
| LLM | Groq API (llama-3.3-70b-versatile) | 100K tokens/day | No CC |
| Web Search | Tavily API | 1,000 req/month | No CC |
| Neural Search | Exa API | 1,000 req/month | No CC |
| Reddit Data | Reddit OAuth API | Unlimited | Requires approved app |
| HN Data | Hacker News Algolia API | Unlimited | Free, no auth |
| Cache | Upstash Redis | 10K cmd/day | No CC |
| Backup Search | Brave Search API | 2,000 req/month | No CC |

---

## Project Structure

```
trendspy/
├── CLAUDE.md              ← You are here
├── PROMPTS.md             ← Ready-to-use Claude Code prompts
├── README.md
├── .gitignore
│
├── backend/               ← FastAPI → Koyeb
│   ├── main.py            ← App entry point + CORS + router registration
│   ├── requirements.txt
│   ├── Procfile           ← Koyeb deploy config
│   ├── .env.example
│   ├── routers/
│   │   ├── analyze.py     ← POST /analyze → SSE StreamingResponse ← CORE
│   │   └── briefs.py      ← GET/POST/DELETE /briefs
│   ├── services/
│   │   ├── tavily_service.py   ← Tavily web search
│   │   ├── exa_service.py      ← Exa neural search
│   │   ├── reddit_service.py   ← Reddit OAuth API (optional)
│   │   ├── hn_service.py       ← Hacker News Algolia API (free, no auth)
│   │   ├── groq_service.py     ← Groq LLM + streaming
│   │   └── cache_service.py    ← Upstash Redis
│   └── models/
│       └── schemas.py     ← Pydantic request/response models
│
└── frontend/              ← React + Vite → Vercel
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    ├── .env.example
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── index.css
        ├── components/
        │   ├── InputForm.jsx        ← Niche input + submit
        │   ├── MarketBriefCard.jsx  ← Displays brief sections progressively
        │   ├── LoadingState.jsx     ← SSE status messages + progress
        │   └── HistoryList.jsx      ← Past briefs list
        ├── pages/
        │   ├── Home.jsx             ← Landing + input
        │   ├── Dashboard.jsx        ← Saved briefs
        │   └── Brief.jsx            ← Single brief view (shareable)
        └── lib/
            ├── supabase.js          ← Supabase client
            ├── api.js               ← SSE client (EventSource wrapper)
            └── utils.js             ← Helpers
```

---

## Environment Variables

### backend/.env
```
GROQ_API_KEY=
TAVILY_API_KEY=
EXA_API_KEY=
BRAVE_SEARCH_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
CORS_ORIGINS=http://localhost:5173
APP_ENV=development
```

### frontend/.env.local
```
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

---

## Supabase Schema

```sql
-- Run in Supabase SQL Editor

CREATE TABLE briefs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  niche_input TEXT NOT NULL,
  pain_points JSONB DEFAULT '[]',
  competitor_gaps JSONB DEFAULT '[]',
  pricing_signals JSONB DEFAULT '{}',
  hot_communities JSONB DEFAULT '[]',
  ai_summary TEXT,
  raw_sources JSONB DEFAULT '[]',
  is_public BOOLEAN DEFAULT false,
  share_slug TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE briefs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own briefs or public"
  ON briefs FOR SELECT
  USING (auth.uid() = user_id OR is_public = true);

CREATE POLICY "Users can insert own briefs"
  ON briefs FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own briefs"
  ON briefs FOR DELETE
  USING (auth.uid() = user_id);

CREATE INDEX briefs_user_id_idx ON briefs(user_id);
CREATE INDEX briefs_share_slug_idx ON briefs(share_slug) WHERE share_slug IS NOT NULL;
```

---

## SSE Protocol (Frontend ↔ Backend Contract)

Backend streams these event types:

```
event: status
data: {"message": "🔍 Scanning Reddit...", "step": 1, "total": 5}

event: status
data: {"message": "✓ Reddit: 23 posts found", "step": 1, "done": true}

event: status
data: {"message": "🧠 AI analyzing...", "step": 3, "total": 5}

event: result
data: {"section": "pain_points", "data": [{...}]}

event: result
data: {"section": "competitor_gaps", "data": [{...}]}

event: result
data: {"section": "pricing_signals", "data": {...}}

event: result
data: {"section": "hot_communities", "data": [{...}]}

event: result
data: {"section": "ai_summary", "data": "string..."}

event: done
data: {"brief_id": "uuid", "duration_seconds": 18}

event: error
data: {"message": "...", "code": "RATE_LIMIT|API_ERROR|TIMEOUT"}
```

---

## Coding Conventions

- **Python**: type hints everywhere, async/await, pydantic models
- **JavaScript**: functional components, hooks only (no class components)
- **Naming**: snake_case Python, camelCase JS, kebab-case CSS classes
- **Error handling**: never swallow errors silently, always yield SSE error event
- **API limits awareness**: cache Tavily/Exa results in Redis to avoid hitting monthly limits
- **No `any` types** in Pydantic models

---

## Hackathon Judging Criteria (keep in mind while building)

1. **Progress** — How much did you build? → Build all core features MVP
2. **Concept** — Does it solve a real problem? → Market research for indie makers
3. **Feasibility** → Freemium $9/month SaaS potential

**Devpost submission needs:**
- Live demo URL (Vercel frontend)
- GitHub repo (public)
- Demo video (2-3 min, screen record)
- Screenshots (5+)

---

## Recommended Claude Model

Use **claude-sonnet-4-5** or **claude-sonnet-4-6** for all coding tasks.
- Fast enough for iterative coding
- Strong Python + React capability
- Use Opus only for complex architectural decisions

---

## Current Status

- [x] Project planning & architecture
- [x] Tech stack verified (all free)
- [x] Backend boilerplate (main.py, services skeleton)
- [x] SSE streaming endpoint (/analyze)
- [x] Frontend components (InputForm, MarketBriefCard, LoadingState, HistoryList)
- [x] Supabase integration (PostgreSQL + Google OAuth)
- [x] Upstash Redis (cache + rate limiting)
- [x] Hacker News data source (Algolia API — no auth)
- [x] Reddit OAuth service (ready — needs approved app)
- [x] Groq AI analysis (llama-3.3-70b-versatile, anti-hallucination prompt)
- [x] Save + share briefs (public links)
- [x] Force-refresh cache feature
- [x] Local dev working end-to-end
- [ ] Deploy Render.com (backend)
- [ ] Deploy Vercel (frontend)
- [ ] Reddit app approval (submitted request)
- [ ] Demo video + Devpost submission (deadline June 10, 2026)
