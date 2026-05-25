from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from models.schemas import AnalyzeRequest
from services import (
    reddit_service, tavily_service, exa_service, groq_service,
    cache_service, hn_service, devto_service, stackexchange_service,
    product_hunt_service,
)
import asyncio
import json
import re
from datetime import datetime, timezone

router = APIRouter()


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _community_hints(niche: str) -> list[str]:
    """Return 5-6 real subreddit suggestions based on niche keywords."""
    n = niche.lower()
    hints: list[str] = []

    # Niche-specific subs first
    if any(w in n for w in ["freelance", "freelancer", "freelancing", "solopreneur"]):
        hints += ["r/freelance", "r/freelancers", "r/solopreneur"]
    if any(w in n for w in ["schedul", "calendar", "booking", "appointment"]):
        hints += ["r/productivity", "r/solopreneur", "r/freelance"]
    if any(w in n for w in ["productiv", "task", "todo", "gtd"]):
        hints += ["r/productivity", "r/getdisciplined", "r/nosurf"]
    if any(w in n for w in ["market", "seo", "ads", "growth", "content"]):
        hints += ["r/marketing", "r/SEO", "r/digitalnomad"]
    if any(w in n for w in ["ai", "artificial", "gpt", "llm", "ml"]):
        hints += ["r/artificial", "r/MachineLearning", "r/ChatGPT"]
    if any(w in n for w in ["ecommerce", "shop", "store", "shopify"]):
        hints += ["r/ecommerce", "r/shopify", "r/dropship"]
    if any(w in n for w in ["design", "ux", "ui", "figma"]):
        hints += ["r/web_design", "r/UXDesign", "r/graphic_design"]
    if any(w in n for w in ["developer", "coding", "code", "dev", "api"]):
        hints += ["r/webdev", "r/programming", "r/learnprogramming"]

    # Always include broad startup subs
    hints += ["r/entrepreneur", "r/SaaS", "r/startups"]

    # Deduplicate, keep order
    seen: set = set()
    result = []
    for s in hints:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result[:6]


def build_context(
    niche: str,
    reddit: list,
    tavily: list,
    exa: list,
    hn: list,
    devto: list = None,
    stackexchange: list = None,
    product_hunt: list = None,
) -> str:
    devto = devto or []
    stackexchange = stackexchange or []
    product_hunt = product_hunt or []

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
    if devto:
        sources_available.append("Dev.to")
    if stackexchange:
        sources_available.append("Stack Exchange")
    if product_hunt:
        sources_available.append("Product Hunt")

    community_hints = _community_hints(niche)

    parts = [f"NICHE: {niche}\n"]
    parts.append(f"AVAILABLE DATA SOURCES: {', '.join(sources_available)}")
    parts.append("IMPORTANT: Only cite these sources. Never invent source names.\n")
    parts.append(
        "SUGGESTED COMMUNITIES (use these exact names in HOT_COMMUNITIES, pick the 3-5 most relevant):\n"
        + "\n".join(community_hints) + "\n"
    )

    if reddit:
        parts.append("REDDIT DISCUSSIONS:")
        for p in reddit[:8]:
            parts.append(f"- [r/{p['subreddit']}] {p['title']} (score: {p['score']})\n  {p['selftext'][:200]}")
    if hn:
        parts.append("\nHACKER NEWS DISCUSSIONS:")
        for h in hn[:6]:
            parts.append(f"- [HN] {h['title']} (points: {h['points']})\n  {h['text'][:200]}")
    if stackexchange:
        parts.append("\nSTACK EXCHANGE Q&A (real user questions = pain points):")
        for q in stackexchange[:8]:
            parts.append(f"- [{q['site']}] {q['title']} (votes: {q['score']})\n  {q['body'][:200]}")
    if product_hunt:
        parts.append("\nPRODUCT HUNT COMPETITORS:")
        for p in product_hunt[:6]:
            parts.append(
                f"- {p['name']}: {p['tagline']} ({p['votes']} votes, "
                f"{p['reviews']} reviews, rating: {p['rating']}/5)\n  {p['description'][:200]}"
            )
    if tavily:
        parts.append("\nWEB SOURCES (Tavily):")
        for r in tavily[:8]:
            parts.append(f"- {r['title']}: {r['content'][:300]}")
    if exa:
        parts.append("\nWEB SOURCES (Exa):")
        for r in exa[:6]:
            parts.append(f"- {r['title']}: {r['text'][:300]}")
    if devto:
        parts.append("\nDEV.TO ARTICLES:")
        for a in devto[:6]:
            parts.append(f"- {a['title']} ({a['reactions']} reactions): {a['content'][:200]}")

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

    # 1. HOT_COMMUNITIES — normalize messy names, filter fakes
    if "hot_communities" in sections and isinstance(sections["hot_communities"], list):
        valid = []
        for c in sections["hot_communities"]:
            raw_name = c.get("name", "").strip()
            name_lower = raw_name.lower()

            # Reject known fake/generic keyword matches
            is_fake = any(fake in name_lower.replace(" ", "") for fake in _FAKE_COMMUNITY_KEYWORDS)
            if is_fake:
                continue

            # Accept known real non-Reddit platforms (exact match)
            if name_lower in _KNOWN_PLATFORMS:
                valid.append(c)
                continue

            # Already in perfect r/subredditname format
            if re.match(r'^r/[A-Za-z0-9_]{2,25}$', raw_name):
                valid.append(c)
                continue

            # Try to EXTRACT a subreddit name from messy strings like
            # "Reddit's r/freelance", "the r/freelancers subreddit", etc.
            m = _SUBREDDIT_RE.search(raw_name)
            if m:
                extracted = f"r/{m.group(1)}"
                # Re-check the extracted name is not fake
                if not any(fake in extracted.lower().replace(" ", "") for fake in _FAKE_COMMUNITY_KEYWORDS):
                    valid.append({**c, "name": extracted})
                continue

        # Fallback: if fewer than 3 valid communities, fill with reliable defaults
        defaults = [
            {"name": "r/entrepreneur", "members": "3.5M", "activity": "high"},
            {"name": "r/SaaS", "members": "200K+", "activity": "high"},
            {"name": "Hacker News", "members": "400K+", "activity": "high"},
            {"name": "r/startups", "members": "600K+", "activity": "high"},
        ]
        existing_names = {c["name"].lower() for c in valid}
        for d in defaults:
            if len(valid) >= 4:
                break
            if d["name"].lower() not in existing_names:
                valid.append(d)
                existing_names.add(d["name"].lower())

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
    # Rate limiting — force=True skips the check so cache-busting is never blocked
    if not force:
        allowed = await cache_service.check_rate_limit(client_ip)
        if not allowed:
            yield sse("error", {"message": "Rate limit reached. Try again in 1 hour.", "code": "RATE_LIMIT"})
            return

    # Check cache (skip if force=True)
    if not force:
        cached = await cache_service.get_cached(niche)
        if cached:
            try:
                cached_obj = json.loads(cached)
            except json.JSONDecodeError:
                cached_obj = {}
            # Extract metadata stored alongside sections
            meta = cached_obj.pop("_meta", {})
            yield sse("status", {"message": "Loading from cache...", "step": 0})
            yield sse("cached", cached_obj)
            yield sse("done", {
                "cached": True,
                "duration_seconds": 0,
                "cached_at": meta.get("cached_at"),
            })
            return

    import time
    start = time.time()

    try:
        # Step 1: All community & web sources in parallel
        yield sse("status", {"message": "Scanning communities & web sources...", "step": 1, "total": 4})
        (
            reddit_data, tavily_data, hn_data,
            devto_data, se_data, ph_data,
        ) = await asyncio.gather(
            reddit_service.search_reddit(niche),
            tavily_service.search_tavily(niche),
            hn_service.search_hn(niche),
            devto_service.search_devto(niche),
            stackexchange_service.search_stackexchange(niche),
            product_hunt_service.search_product_hunt(niche),
        )
        # Build a readable source count summary
        source_counts = []
        if reddit_data:  source_counts.append(f"{len(reddit_data)} Reddit")
        if hn_data:      source_counts.append(f"{len(hn_data)} HN")
        if devto_data:   source_counts.append(f"{len(devto_data)} Dev.to")
        if se_data:      source_counts.append(f"{len(se_data)} Stack Exchange")
        if ph_data:      source_counts.append(f"{len(ph_data)} Product Hunt")
        source_counts.append(f"{len(tavily_data)} Tavily")
        yield sse("status", {"message": f"✓ {' + '.join(source_counts)} found", "step": 1, "done": True})

        # Step 2: Exa neural search
        yield sse("status", {"message": "Running neural search...", "step": 2, "total": 4})
        exa_data = await exa_service.search_exa(niche)
        yield sse("status", {"message": f"✓ {len(exa_data)} additional sources from neural search", "step": 2, "done": True})

        # Step 3: AI Analysis
        yield sse("status", {"message": "AI analyzing all data points...", "step": 3, "total": 4})
        context = build_context(
            niche, reddit_data, tavily_data, exa_data, hn_data,
            devto_data, se_data, ph_data,
        )

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

        # Cache the result — include _meta so UI can show "cached X min ago"
        cache_payload = {
            **sections,
            "_meta": {"cached_at": datetime.now(timezone.utc).isoformat()},
        }
        await cache_service.set_cache(niche, json.dumps(cache_payload))

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
