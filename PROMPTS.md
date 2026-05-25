# PROMPTS.md — Siap Pakai di Claude Code

> Copy-paste prompt ini langsung ke Claude Code (claude-sonnet-4-5 atau claude-sonnet-4-6).
> Urutan pengerjaan sudah diatur dari atas ke bawah.
> Baca CLAUDE.md dulu sebelum mulai — Claude Code akan otomatis membacanya.

---

## 📋 CARA PAKAI

1. Buka folder `trendspy/` di Claude Code
2. Claude Code akan baca `CLAUDE.md` otomatis
3. Copy prompt di bawah sesuai urutan, paste ke Claude Code
4. Setelah setiap prompt selesai, lanjut ke prompt berikutnya

---

## PROMPT 1 — Backend Setup & Dependencies

```
Baca CLAUDE.md untuk context project ini.

Setup backend FastAPI TrendSpy:

1. Buat `backend/requirements.txt` dengan dependencies:
   - fastapi, uvicorn[standard]
   - httpx (async HTTP client)
   - groq (official SDK)
   - supabase (python client)
   - upstash-redis
   - python-dotenv
   - pydantic

2. Buat `backend/Procfile`:
   web: uvicorn main:app --host 0.0.0.0 --port 8000

3. Buat `backend/main.py` dengan:
   - FastAPI app instance
   - CORS middleware (baca CORS_ORIGINS dari env)
   - Include router dari routers/analyze.py dan routers/briefs.py
   - Health check GET /health → {"status": "ok", "version": "1.0.0"}
   - Lifespan event untuk init Redis connection

4. Buat `backend/models/schemas.py` dengan Pydantic models:
   - AnalyzeRequest: niche_input (str, min 3 chars, max 200 chars)
   - PainPoint: text, frequency (int), source (str)
   - CompetitorGap: competitor, gap, opportunity
   - PricingSignals: competitor_range, willingness_to_pay, insights (list[str])
   - Community: name, members, activity (high/medium/low)
   - BriefResult: pain_points, competitor_gaps, pricing_signals, hot_communities, ai_summary
   - SaveBriefRequest: niche_input, result (BriefResult)

5. Buat `backend/.env.example` dengan semua env vars dari CLAUDE.md

Gunakan async/await dan type hints di semua fungsi.
```

---

## PROMPT 2 — Services Layer (Data Fetching)

```
Baca CLAUDE.md untuk context.

Buat semua service files di backend/services/:

1. `backend/services/reddit_service.py`
   - Fungsi: async def search_reddit(niche: str) -> list[dict]
   - Pakai Reddit JSON API (TANPA auth): GET https://www.reddit.com/search.json?q={query}&sort=top&t=year&limit=25
   - Tambah header User-Agent: "TrendSpy/1.0 (hackathon project)"
   - Query: f"{niche} problems pain points complaints"
   - Return list of {title, selftext, score, subreddit, url}
   - Handle rate limit dengan retry sekali setelah 2 detik
   - Timeout: 10 detik

2. `backend/services/tavily_service.py`
   - Fungsi: async def search_tavily(niche: str) -> list[dict]
   - POST https://api.tavily.com/search
   - Body: {"api_key": TAVILY_KEY, "query": f"{niche} alternatives competitors pricing", "search_depth": "basic", "max_results": 5}
   - Return list of {title, url, content, score}
   - Timeout: 15 detik

3. `backend/services/exa_service.py`
   - Fungsi: async def search_exa(niche: str) -> list[dict]
   - POST https://api.exa.ai/search
   - Headers: {"x-api-key": EXA_KEY, "Content-Type": "application/json"}
   - Body: {"query": f"{niche} market size user feedback review", "numResults": 5, "contents": {"text": true}}
   - Return list of {title, url, text}
   - Timeout: 15 detik

4. `backend/services/groq_service.py`
   - Fungsi: async def analyze_with_groq(niche: str, raw_data: str) -> AsyncGenerator[str, None]
   - Pakai Groq SDK, model: "llama-3.1-8b-instant"
   - Stream: True
   - System prompt yang menghasilkan JSON structured output sesuai BriefResult schema
   - Yield chunks of text as they stream
   - Handle Groq rate limit (429) dengan yield error message

5. `backend/services/cache_service.py`
   - Pakai upstash-redis
   - async def get_cached(key: str) -> str | None
   - async def set_cache(key: str, value: str, ttl: int = 3600) -> None
   - Cache key: hashlib.md5(niche.lower().strip().encode()).hexdigest()
   - TTL: 1 jam

Semua service harus handle exception dan raise HTTPException yang meaningful.
```

---

## PROMPT 3 — SSE Streaming Endpoint (Core Feature)

```
Baca CLAUDE.md — khususnya bagian "SSE Protocol" dan "Key UX Mechanic".

Buat `backend/routers/analyze.py` dengan SSE streaming endpoint:

POST /analyze
- Terima AnalyzeRequest (niche_input)
- Return StreamingResponse dengan media_type="text/event-stream"
- Headers: Cache-Control: no-cache, X-Accel-Buffering: no

Flow yang harus diimplementasikan:
1. Cek cache Redis → jika ada, stream langsung hasilnya dengan event "cached: true"
2. Yield SSE event "status": {"message": "🔍 Scanning Reddit...", "step": 1}
3. Jalankan reddit_service.search_reddit() 
4. Yield SSE event "status": {"message": "✓ Reddit: N posts found", "done": true}
5. Yield SSE event "status": {"message": "🌐 Crawling web sources...", "step": 2}
6. Jalankan tavily + exa SECARA PARALEL dengan asyncio.gather()
7. Yield SSE event "status": {"message": "✓ Web data gathered", "done": true}
8. Yield SSE event "status": {"message": "🧠 AI analyzing...", "step": 3}
9. Gabungkan semua data jadi string context untuk Groq
10. Stream Groq response, parse JSON sections saat datang
11. Untuk setiap section yang selesai di-parse, yield SSE event "result"
12. Simpan ke Redis cache
13. Yield SSE event "done" dengan duration

Format SSE sesuai protokol di CLAUDE.md.

Helper function: def format_sse(event: str, data: dict) -> str:
  return f"event: {event}\ndata: {json.dumps(data)}\n\n"

Handle semua exceptions: yield SSE "error" event, jangan biarkan stream crash tanpa notif ke client.
```

---

## PROMPT 4 — Briefs CRUD + Supabase

```
Baca CLAUDE.md untuk schema Supabase.

1. Buat `backend/routers/briefs.py`:
   - POST /briefs — simpan brief ke Supabase (butuh user token di header)
   - GET /briefs — ambil semua brief milik user (dari Supabase, filter by user_id)
   - GET /briefs/{id} — ambil satu brief (cek owner atau is_public)
   - DELETE /briefs/{id} — hapus brief (cek owner)
   - POST /briefs/{id}/share — set is_public=true, generate share_slug (nanoid 8 char)
   - GET /share/{slug} — ambil brief via share slug (public, no auth)

2. Auth middleware:
   - Baca JWT dari Authorization: Bearer {token}
   - Verifikasi dengan Supabase JWT secret atau pakai supabase-py
   - Inject user_id ke request state

3. Pastikan semua endpoint di atas sudah ada di Supabase (jalankan SQL dari CLAUDE.md).

Gunakan supabase-py async client.
```

---

## PROMPT 5 — Frontend Setup & Routing

```
Baca CLAUDE.md untuk context.

Setup frontend React TrendSpy di folder frontend/:

1. Pastikan package.json sudah ada dengan dependencies:
   - react, react-dom, react-router-dom
   - @supabase/supabase-js
   - lucide-react
   - clsx, tailwind-merge
   - axios

2. Buat `frontend/src/lib/supabase.js`:
   - createClient dengan VITE_SUPABASE_URL dan VITE_SUPABASE_ANON_KEY
   - Export supabase client

3. Buat `frontend/src/lib/api.js`:
   - Fungsi: createAnalysisStream(niche, callbacks)
   - Buka EventSource ke {VITE_API_BASE_URL}/analyze (POST via fetch + ReadableStream, bukan EventSource karena POST)
   - Callbacks: onStatus(msg), onResult(section, data), onDone(briefId, duration), onError(msg)
   - Handle connection errors gracefully

4. Buat `frontend/src/App.jsx` dengan React Router:
   - "/" → Home page
   - "/dashboard" → Dashboard (protected, butuh login)
   - "/brief/:id" → Single brief
   - "/share/:slug" → Public brief
   - Auth state dari Supabase onAuthStateChange

5. Setup Tailwind dengan dark theme sebagai default (class "dark" di html tag)

Color palette dari CLAUDE.md:
- Background: #0A0A0B
- Card: #111113
- Border: #1E1E24
- Primary: #7C3AED
- Accent: #10B981
- Text: #F4F4F5
- Muted: #71717A
```

---

## PROMPT 6 — Frontend Components (Core UI)

```
Baca CLAUDE.md untuk UX flow dan SSE protocol.

Buat semua komponen di frontend/src/components/:

1. `InputForm.jsx`:
   - Textarea untuk niche input (placeholder: "e.g. AI scheduling tool for freelancers")
   - Character counter (max 200)
   - Submit button dengan loading state
   - Validation: min 3 karakter
   - On submit: panggil api.js createAnalysisStream()

2. `LoadingState.jsx`:
   - Terima prop: steps (array of {message, done, active})
   - Tampilkan setiap step dengan icon: ⏳ (pending), 🔄 (active, animated pulse), ✓ (done)
   - Animated progress bar di bawah
   - Feel "alive" — step yang aktif harus ada pulse animation

3. `MarketBriefCard.jsx`:
   - Terima prop: briefData (pain_points, competitor_gaps, pricing_signals, hot_communities, ai_summary)
   - Render setiap section sebagai card terpisah dengan icon dan warna
   - 🔥 Pain Points — merah muda, list items dengan frequency badge
   - 🕳️ Competitor Gaps — kuning, tabel competitor vs gap vs opportunity
   - 💰 Pricing Signals — hijau, range + insights
   - 🗺️ Hot Communities — ungu, list dengan member count badge
   - 🧠 AI Summary — biru, paragraph teks
   - Setiap section muncul dengan fade-in animation saat data tersedia
   - "Share" dan "Save" button di atas

4. `HistoryList.jsx`:
   - List card brief yang pernah dibuat
   - Tampilkan: niche_input, tanggal, tombol view & delete
   - Loading skeleton saat fetch

Gunakan shadcn/ui components jika ada (Button, Card, Badge, Textarea).
Semua komponen harus responsive (mobile-friendly).
```

---

## PROMPT 7 — Pages

```
Buat semua pages di frontend/src/pages/:

1. `Home.jsx`:
   - Hero section: tagline "Market research in 2 minutes, not 2 weeks"
   - Sub: "Discover real pain points, competitor gaps & pricing signals from live web data"
   - InputForm component di tengah
   - State machine: idle → loading → results
   - Saat loading: tampilkan LoadingState dengan SSE steps
   - Saat results: tampilkan MarketBriefCard
   - Tombol "Save brief" (butuh login) dan "Share" (langsung generate link)
   - Jika belum login dan klik Save: tampilkan auth modal

2. `Dashboard.jsx`:
   - Protected route (redirect ke home jika belum login)
   - Header: "Your Market Briefs"
   - HistoryList component
   - Empty state: ilustrasi + "Analyze your first niche"

3. `Brief.jsx`:
   - Fetch brief by ID dari Supabase
   - Tampilkan MarketBriefCard dengan data tersimpan
   - "Analyze again" button (re-run dengan niche yang sama)

4. `Brief.jsx` untuk share route (/share/:slug):
   - Fetch brief by share_slug (public endpoint)
   - Tampilkan MarketBriefCard read-only
   - "Try TrendSpy free" CTA di bawah

Tambahkan Navbar minimal di App.jsx:
- Logo "TrendSpy" kiri
- "Dashboard" link (jika logged in)
- Login/Logout button kanan (Supabase Auth UI atau custom modal)
```

---

## PROMPT 8 — Auth Integration

```
Integrasikan Supabase Auth ke TrendSpy frontend:

1. Buat AuthModal component:
   - Modal dengan 2 tab: Sign In / Sign Up
   - Input: email + password
   - Pakai supabase.auth.signInWithPassword() dan supabase.auth.signUp()
   - Tambahkan Google OAuth: supabase.auth.signInWithOAuth({provider: 'google'})
   - Loading state, error handling
   - Auto-close setelah berhasil login

2. Update App.jsx:
   - supabase.auth.onAuthStateChange() untuk track session
   - Simpan user di React context atau state
   - Pass user ke semua pages yang butuh

3. Update Home.jsx:
   - Jika user belum login, tampilkan: "3 free briefs remaining" (mock counter)
   - Jika user login, tampilkan: "Save Brief" button yang aktif

4. Pass Supabase JWT token ke backend saat call POST /briefs:
   - Ambil session.access_token dari supabase.auth.getSession()
   - Sertakan di header: Authorization: Bearer {token}

Setup Supabase Google OAuth di dashboard Supabase:
- Authentication → Providers → Google → enable
- (instruksi untuk user: masukkan Google Client ID & Secret)
```

---

## PROMPT 9 — Polish, Error Handling & Performance

```
Polish TrendSpy sebelum deploy:

1. Error boundaries:
   - Tambahkan React ErrorBoundary di App.jsx
   - Graceful fallback UI jika komponen crash

2. Loading skeletons:
   - Tambahkan skeleton loader di HistoryList saat fetch
   - Skeleton di Brief page saat load

3. Toast notifications:
   - Sukses: "Brief saved!" "Link copied!"
   - Error: "Analysis failed, try again" "Rate limit reached, wait 1 minute"
   - Buat simple Toast component sendiri (no library) atau pakai shadcn Sonner

4. Rate limiting di backend:
   - Di cache_service.py, tambahkan fungsi check_rate_limit(ip: str) -> bool
   - Max 10 requests per IP per jam
   - Return 429 dengan SSE error event jika exceeded

5. Mobile responsiveness check:
   - MarketBriefCard harus readable di mobile (max-width: 375px)
   - InputForm textarea resize dengan konten
   - Navbar collapse ke hamburger di mobile (jika ada menu)

6. SEO & meta tags:
   - Update index.html dengan proper title, description, og:image
   - Share page harus punya dynamic meta tags

7. Performance:
   - Lazy load Dashboard dan Brief pages dengan React.lazy()
   - Memoize MarketBriefCard dengan React.memo()
```

---

## PROMPT 10 — Deploy

```
Deploy TrendSpy ke production:

BACKEND (Koyeb):
1. Pastikan Procfile ada: web: uvicorn main:app --host 0.0.0.0 --port 8000
2. Push backend ke GitHub (bisa subfolder atau repo terpisah)
3. Di Koyeb dashboard:
   - New Service → GitHub → pilih repo
   - Root directory: backend/
   - Instance type: free (WAJIB pilih ini, jangan yang lain)
   - Set semua env vars dari .env.example
4. Setelah deploy, catat URL: https://xxx.koyeb.app

FRONTEND (Vercel):
1. Push seluruh project ke GitHub
2. Di Vercel: New Project → Import repo
3. Framework: Vite
4. Root directory: frontend/
5. Set env vars:
   - VITE_API_BASE_URL = https://xxx.koyeb.app (URL dari Koyeb)
   - VITE_SUPABASE_URL = (dari Supabase dashboard)
   - VITE_SUPABASE_ANON_KEY = (dari Supabase dashboard)
6. Deploy → catat URL Vercel

SETELAH DEPLOY:
1. Update CORS_ORIGINS di Koyeb env ke URL Vercel production
2. Update Supabase Auth → URL Configuration → Site URL ke URL Vercel
3. Test full flow: input niche → SSE stream → save → share link

DEVPOST SUBMISSION:
1. Live Demo URL: URL Vercel
2. GitHub repo: set ke PUBLIC
3. Rekam demo video 2-3 menit (pakai screen recorder)
4. Screenshot 5 halaman utama
5. Submit ke: Overall Winner + name.com Domain Roulette
```

---

## PROMPT BONUS — Groq Prompt Engineering

```
Optimasi prompt di backend/services/groq_service.py untuk output terbaik:

System prompt harus:
1. Instruksikan Groq untuk output JSON yang bisa di-parse bertahap
2. Setiap section harus dimulai dengan marker: ###PAIN_POINTS###, ###GAPS###, dll
3. Ini memudahkan parsing streaming response section per section

Template prompt:
---
You are a market intelligence analyst. Analyze the following web data about: "{niche}"

Return your analysis with section markers exactly as shown:

###PAIN_POINTS###
[{"text": "specific pain point from data", "frequency": 45, "source": "Reddit"}]

###COMPETITOR_GAPS###
[{"competitor": "name", "gap": "what they're missing", "opportunity": "how to capitalize"}]

###PRICING_SIGNALS###
{"competitor_range": "$X-Y/month", "willingness_to_pay": "$A-B/month", "insights": ["insight 1", "insight 2"]}

###HOT_COMMUNITIES###
[{"name": "r/example", "members": "100K", "activity": "high"}]

###AI_SUMMARY###
2-3 sentence actionable summary for a founder considering this space.

Rules:
- Only use information from the provided data
- Be specific with numbers when available
- Frequency = estimated number of mentions/discussions
- Maximum 5 items per list section
---

Web data to analyze:
{raw_data}

Buat parser di analyze.py yang detect markers saat streaming dan emit SSE "result" event per section.
```

---

## Quick Reference

```bash
# Run backend locally
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Run frontend locally  
cd frontend && npm install && npm run dev

# Test SSE endpoint
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"niche_input": "AI scheduling for freelancers"}' \
  --no-buffer
```
