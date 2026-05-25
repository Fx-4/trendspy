"""
Dev.to API service — free, no auth required.
Returns developer community articles relevant to the niche.
Quality filter: min 10 reactions, published ≤3 years ago, relevant to niche.
"""
import httpx
import asyncio
import re
from services.data_quality import filter_items

DEVTO_API = "https://dev.to/api"

# Map niche keywords → relevant Dev.to tags
_TAG_MAP = {
    "saas": ["saas", "startup", "business"],
    "freelance": ["freelance", "productivity", "business"],
    "scheduling": ["productivity", "tools", "saas"],
    "ai": ["ai", "machinelearning", "openai"],
    "productivity": ["productivity", "tools", "workflow"],
    "marketing": ["marketing", "seo", "growth"],
    "ecommerce": ["ecommerce", "shopify", "business"],
    "finance": ["fintech", "money", "business"],
    "developer": ["webdev", "programming", "career"],
    "design": ["design", "ux", "webdev"],
    "health": ["healthtech", "fitness", "wellness"],
    "education": ["education", "learning", "career"],
    "remote": ["remote", "productivity", "career"],
}

_FALLBACK_TAGS = ["saas", "startup"]


def _extract_tags(niche: str) -> list[str]:
    niche_lower = niche.lower()
    tags = []
    for keyword, mapped in _TAG_MAP.items():
        if keyword in niche_lower:
            tags.extend(mapped)
    if not tags:
        tags = _FALLBACK_TAGS
    # Also try niche words directly as tags
    words = [re.sub(r'[^a-z0-9]', '', w) for w in niche_lower.split() if len(w) > 3]
    tags = list(dict.fromkeys(words[:2] + tags))  # deduplicate, keep order
    return tags[:4]


async def _fetch_articles(client: httpx.AsyncClient, tag: str) -> list[dict]:
    try:
        r = await client.get(
            f"{DEVTO_API}/articles",
            params={"tag": tag, "per_page": 15, "top": 30},
            timeout=8.0,
        )
        r.raise_for_status()
        articles = r.json()
        return [
            {
                "title": a.get("title", ""),
                "content": (a.get("description") or "")[:400],
                "url": a.get("url", ""),
                "reactions": a.get("public_reactions_count", 0),
                "published_at": a.get("published_at", ""),
                "source": "Dev.to",
                "tag": tag,
            }
            for a in articles
            if a.get("title")
            and a.get("public_reactions_count", 0) >= 10  # min 10 reactions = community-validated
            and len(a.get("description") or "") >= 50     # must have real content
        ]
    except Exception:
        return []


async def search_devto(niche: str) -> list[dict]:
    """Search Dev.to articles. Only returns community-validated, niche-relevant content."""
    tags = _extract_tags(niche)

    async with httpx.AsyncClient() as client:
        tasks = [_fetch_articles(client, tag) for tag in tags]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_articles = []
    for r in results:
        if isinstance(r, list):
            all_articles.extend(r)

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in sorted(all_articles, key=lambda x: x["reactions"], reverse=True):
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    # Apply quality + relevance filter
    return filter_items(
        unique,
        niche=niche,
        title_key="title",
        content_key="content",
        score_key="reactions",
        min_score=10,
        date_key="published_at",
        max_years=3,
        min_relevance=0.15,
        limit=10,
    )
