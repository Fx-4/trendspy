# TrendSpy

> Real-time market intelligence for indie makers — in under 60 seconds.

**DeveloperWeek New York 2026 Hackathon submission.**

---

## What it does

Founders waste weeks doing market research manually. TrendSpy cuts that to under a minute.

Type any niche or product idea → TrendSpy crawls **Hacker News**, **Tavily web search**, **Exa neural search**, and optionally **Reddit** in parallel → streams back a structured **Market Intelligence Brief** powered by Groq AI.

**You get:**
- Top pain points (with source + estimated frequency)
- Competitor gaps and how to beat them
- Pricing signals (competitor range + willingness to pay)
- Hot communities where your target users hang out
- AI summary with actionable founder insight

**Live demo:** https://trendspy.vercel.app

---

## Why it's different

Most market research tools are slow, expensive, or generic. TrendSpy is:

- **Real-time** — live data crawled at query time, not a static database
- **Streaming** — results appear progressively via SSE, not a 30s spinner
- **Free-tier only** — built entirely on free APIs (no credit card needed to run)
- **Founder-focused** — output is structured for decisions, not raw search results

---

## Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| Frontend | React + Vite + Tailwind CSS | Deployed on Vercel |
| Backend | FastAPI (Python) | Deployed on Render.com |
| LLM | Groq API — `llama-3.3-70b-versatile` | Streaming inference |
| Web Search | Tavily API | Real-time web crawl |
| Neural Search | Exa API | Semantic search |
| Community Data | Hacker News Algolia API | Free, no auth |
| Community Data | Reddit OAuth API | Optional, requires app approval |
| Database | Supabase PostgreSQL | Save & share briefs |
| Auth | Supabase Auth (Google OAuth) | One-click sign in |
| Cache | Upstash Redis | 1-hour cache per niche |

**All services used are on their free tier.**

---

## Architecture

```
Browser (React)
    │  POST /analyze { niche_input }
    ▼
FastAPI Backend
    ├── asyncio.gather() ──► Hacker News Algolia API (free)
    │                  ──► Tavily web search
    │                  ──► Reddit OAuth API (if configured)
    │
    ├── Exa neural search
    │
    ├── Build context string (sources + data)
    │
    └── Groq llama-3.3-70b-versatile (streaming)
            │
            ▼  SSE chunks
    Browser renders sections progressively
```

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys: Groq, Tavily, Exa (all free, no CC required)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/trendspy.git
cd trendspy
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

cp .env.example .env
# Edit .env and fill in your API keys
```

### 3. Frontend setup

```bash
cd frontend
npm install

cp .env.example .env.local
# Edit .env.local and fill in your Supabase keys
```

### 4. Run both servers

**Backend** (terminal 1):
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Frontend** (terminal 2):
```bash
cd frontend
npm run dev
```

Open http://localhost:5173

---

## Environment Variables

### `backend/.env`
```
GROQ_API_KEY=          # groq.com → free
TAVILY_API_KEY=        # tavily.com → free
EXA_API_KEY=           # exa.ai → free
SUPABASE_URL=          # supabase.com
SUPABASE_SERVICE_ROLE_KEY=
supabase_anon_key=
UPSTASH_REDIS_REST_URL=    # upstash.com → free
UPSTASH_REDIS_REST_TOKEN=
REDDIT_CLIENT_ID=      # optional — reddit.com/prefs/apps
REDDIT_CLIENT_SECRET=
REDDIT_USERNAME=
CORS_ORIGINS=http://localhost:5173
APP_ENV=development
```

### `frontend/.env.local`
```
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_API_BASE_URL=http://localhost:8000
```

---

## Features

- [x] Real-time SSE streaming (results appear live, no spinner)
- [x] Parallel data fetching (HN + Tavily + Exa simultaneously)
- [x] AI-powered structured analysis (Groq llama-3.3-70b-versatile)
- [x] Anti-hallucination guardrails (strict community + source validation)
- [x] 1-hour Redis cache (avoids redundant API calls)
- [x] Force-refresh button (bypass cache when needed)
- [x] Google OAuth sign-in (Supabase Auth)
- [x] Save briefs to your account
- [x] Share public link for any brief
- [x] Dashboard with brief history
- [x] Rate limiting (10 requests/hour per IP)
- [x] Reddit OAuth support (when credentials available)

---

## Project Structure

```
trendspy/
├── README.md
├── .gitignore
├── CLAUDE.md              ← AI coding context
│
├── backend/               ← FastAPI → Render.com
│   ├── main.py
│   ├── requirements.txt
│   ├── Procfile
│   ├── .env.example
│   ├── routers/
│   │   ├── analyze.py     ← POST /analyze (SSE streaming core)
│   │   └── briefs.py      ← CRUD for saved briefs
│   ├── services/
│   │   ├── groq_service.py
│   │   ├── tavily_service.py
│   │   ├── exa_service.py
│   │   ├── hn_service.py
│   │   ├── reddit_service.py
│   │   └── cache_service.py
│   └── models/
│       └── schemas.py
│
└── frontend/              ← React + Vite → Vercel
    ├── src/
    │   ├── components/
    │   │   ├── InputForm.jsx
    │   │   ├── MarketBriefCard.jsx
    │   │   ├── LoadingState.jsx
    │   │   └── HistoryList.jsx
    │   ├── pages/
    │   │   ├── Home.jsx
    │   │   ├── Dashboard.jsx
    │   │   └── SharedBrief.jsx
    │   └── lib/
    │       ├── api.js         ← SSE client
    │       ├── supabase.js
    │       └── utils.js
    └── package.json
```

---

## License

MIT
