from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from models.schemas import AnalyzeRequest
from services import reddit_service, tavily_service, exa_service, groq_service, cache_service, hn_service
import asyncio
import json
import re

router = APIRouter()


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def build_context(niche: str, reddit: list, tavily: list, exa: list, hn: list) -> str:
    # Tell the AI exactly which sources contributed data
    sources_available = []
    if reddit:
        sources_available.append("Reddit")
    if hn:
        sources_available.append("Hacker News")
    if tavily:
        sources_available.append("Tavily")
    if exa:
        sources_available.append("Exa")

    parts = [f"NICHE: {niche}\n"]
    parts.append(f"AVAILABLE DATA SOURCES: {', '.join(sources_available)}")
    parts.append("IMPORTANT: Only cite these sources. Never add 'Reddit' as a source if it is not listed above.\n")

    if reddit:
        parts.append("REDDIT DISCUSSIONS:")
        for p in reddit[:10]:
            parts.append(f"- [r/{p['subreddit']}] {p['title']} (score: {p['score']})\n  {p['selftext'][:200]}")
    if hn:
        parts.append("\nHACKER NEWS DISCUSSIONS:")
        for h in hn[:8]:
            parts.append(f"- [HN] {h['title']} (points: {h['points']})\n  {h['text'][:200]}")
    if tavily:
        parts.append("\nWEB SOURCES (Tavily):")
        for r in tavily:
            parts.append(f"- {r['title']}: {r['content'][:300]}")
    if exa:
        parts.append("\nWEB SOURCES (Exa):")
        for r in exa:
            parts.append(f"- {r['title']}: {r['text'][:300]}")
    return "\n".join(parts)


# Known fake/hallucinated community patterns to reject
_FAKE_COMMUNITY_KEYWORDS = {
    "startuptribunal", "usereviews", "productivityapps", "saasreviews",
    "startupreview", "startupwatch", "techstartups", "appreviews",
    "toolreviews", "startupinsights", "freelanceforum", "upworkcommunity",
    "fiverr", "freelancers union", "freelancersunion", "guru.com",
    "toptalcommunity", "99designs",
}
# Known real non-Reddit platforms
_KNOWN_PLATFORMS = {
    "hacker news", "news.ycombinator.com", "product hunt", "indie hackers",
    "indiehackers.com", "dev.to", "hashnode", "lobste.rs",
}

# Regex to extract a valid subreddit name from any string (handles "Reddit's r/foo", "r/foo", etc.)
_SUBREDDIT_RE = re.compile(r'r/([A-Za-z0-9_]{2,25})\b')


def validate_sections(sections: dict) -> dict:
    """Post-process AI output: filter fake communities, remove template text."""

    # 1. HOT_COMMUNITIES — strict: ONLY accept exact r/name format or known platforms
    if "hot_communities" in sections and isinstance(sections["hot_communities"], list):
        valid = []
        for c in sections["hot_communities"]:
            name = c.get("name", "").strip()
            name_lower = name.lower()

            # Reject known fake/generic names
            is_fake = any(fake in name_lower.replace(" ", "") for fake in _FAKE_COMMUNITY_KEYWORDS)
            if is_fake:
                continue

            # ONLY accept names in exact "r/subredditname" format (anchored, no extra text)
            is_clean_subreddit = bool(re.match(r'^r/[A-Za-z0-9_]{2,25}$', name))

            # Accept known real non-Reddit platforms (exact match)
            is_known = name_lower in _KNOWN_PLATFORMS

            if is_clean_subreddit or is_known:
                valid.append(c)

        # Fallback defaults if fewer than 2 valid communities survived
        if len(valid) < 2:
            valid = [
                {"name": "r/entrepreneur", "members": "3.5M", "activity": "high"},
                {"name": "r/SaaS", "members": "200K+", "activity": "high"},
                {"name": "Hacker News", "members": "400K+", "activity": "high"},
            ]
        sections["hot_communities"] = valid[:5]

    # 2. PRICING_SIGNALS — remove "key insight X" template placeholders
    # Works on both dict (parsed JSON) and raw string (parse failed)
    ps = sections.get("pricing_signals")
    if isinstance(ps, dict):
        insights = ps.get("insights", [])
        if isinstance(insights, list):
            real = [
                i for i in insights
                if i
                and not re.match(r'^key\s+insight', i.lower().strip())
                and len(i.strip()) > 20
            ]
            ps["insights"] = real if real else [
                "Pricing varies by plan — most competitors offer free + paid tiers",
                "Free plan availability is a key differentiator in this space",
            ]
    elif isinstance(ps, str):
        # JSON parse failed — try to extract the dict from raw text
        try:
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', ps).strip()
            cleaned = re.sub(r'\n?```\s*$', '', cleaned).strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                sections["pricing_signals"] = parsed
                # Re-run the insights filter on the now-parsed dict
                insights = parsed.get("insights", [])
                real = [
                    i for i in insights
                    if i and not re.match(r'^key\s+insight', i.lower().strip()) and len(i.strip()) > 20
                ]
                parsed["insights"] = real if real else [
                    "Pricing varies by plan — most competitors offer free + paid tiers",
                    "Free plan availability is a key differentiator in this space",
                ]
        except (json.JSONDecodeError, Exception):
            pass

    return sections


async def analysis_generator(niche: str, client_ip: str, force: bool = False):
    # Rate limiting
    allowed = await cache_service.check_rate_limit(client_ip)
    if not allowed:
        yield sse("error", {"message": "Rate limit reached. Try again in 1 hour.", "code": "RATE_LIMIT"})
        return

    # Check cache (skip if force=True)
    if not force:
        cached = await cache_service.get_cached(niche)
        if cached:
            yield sse("status", {"message": "Loading from cache...", "step": 0})
            yield sse("cached", json.loads(cached))
            yield sse("done", {"cached": True, "duration_seconds": 0})
            return

    import time
    start = time.time()

    try:
        # Step 1: Reddit + Tavily + HN all in parallel
        yield sse("status", {"message": "Scanning communities & web sources...", "step": 1, "total": 4})
        reddit_data, tavily_data, hn_data = await asyncio.gather(
            reddit_service.search_reddit(niche),
            tavily_service.search_tavily(niche),
            hn_service.search_hn(niche),
        )
        reddit_msg = f"{len(reddit_data)} Reddit + " if reddit_data else ""
        hn_msg = f"{len(hn_data)} HN + " if hn_data else ""
        yield sse("status", {"message": f"✓ {reddit_msg}{hn_msg}{len(tavily_data)} web sources found", "step": 1, "done": True})

        # Step 2: Exa neural search
        yield sse("status", {"message": "Running neural search...", "step": 2, "total": 4})
        exa_data = await exa_service.search_exa(niche)
        yield sse("status", {"message": f"✓ {len(exa_data)} additional sources from neural search", "step": 2, "done": True})

        # Step 3: AI Analysis
        yield sse("status", {"message": "AI analyzing all data points...", "step": 3, "total": 4})
        context = build_context(niche, reddit_data, tavily_data, exa_data, hn_data)

        # Stream and parse Groq response
        full_response = ""
        async for chunk in groq_service.analyze_stream(niche, context):
            full_response += chunk

        # Parse sections from full response
        sections = parse_sections(full_response)
        sections = validate_sections(sections)

        # Emit each section
        for section_name, section_data in sections.items():
            yield sse("result", {"section": section_name, "data": section_data})

        yield sse("status", {"message": "✅ Analysis complete!", "step": 4, "done": True})

        # Cache the result
        await cache_service.set_cache(niche, json.dumps(sections))

        duration = round(time.time() - start, 1)
        yield sse("done", {"duration_seconds": duration, "cached": False})

    except Exception as e:
        yield sse("error", {"message": f"Analysis failed: {str(e)}", "code": "API_ERROR"})


def parse_sections(text: str) -> dict:
    """Parse section markers from Groq streaming output."""
    sections = {}
    markers = {
        "pain_points": "###PAIN_POINTS###",
        "competitor_gaps": "###COMPETITOR_GAPS###",
        "pricing_signals": "###PRICING_SIGNALS###",
        "hot_communities": "###HOT_COMMUNITIES###",
        "ai_summary": "###AI_SUMMARY###",
    }

    for key, marker in markers.items():
        if marker not in text:
            continue
        start = text.index(marker) + len(marker)
        # Find next marker or end
        next_positions = [text.index(m) for m in markers.values() if m in text and text.index(m) > start]
        end = min(next_positions) if next_positions else len(text)
        raw = text[start:end].strip()

        # Strip markdown code fences that LLMs sometimes add (```json ... ```)
        raw = re.sub(r'^```(?:json)?\s*\n?', '', raw).strip()
        raw = re.sub(r'\n?```\s*$', '', raw).strip()

        try:
            sections[key] = json.loads(raw)
        except json.JSONDecodeError:
            sections[key] = raw  # fallback to raw string

    return sections


@router.post("/analyze")
async def analyze(request: Request, body: AnalyzeRequest):
    client_ip = request.client.host if request.client else "unknown"
    return StreamingResponse(
        analysis_generator(body.niche_input, client_ip, body.force),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )
