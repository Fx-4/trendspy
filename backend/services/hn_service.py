"""
Hacker News API service — free, no auth needed.
Quality filter: min 10 points, has real text content, ≤3 years old.
Points on HN = community validation by technical founders/makers.
"""
import httpx
import asyncio
from services.data_quality import filter_items

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


async def search_hn(niche: str) -> list[dict]:
    """Search Hacker News via Algolia API. Returns community-validated posts only."""
    queries = [
        f"{niche} pain points",
        f"{niche} alternatives",
        f"Ask HN: {niche}",
        f"{niche} show HN",
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [_fetch_hn(client, q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items = []
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)

    # Deduplicate by objectID
    seen = set()
    unique = []
    for item in sorted(all_items, key=lambda x: x.get("points", 0), reverse=True):
        oid = item.get("objectID")
        if oid and oid not in seen:
            seen.add(oid)
            unique.append(item)

    # Apply quality + relevance filter
    return filter_items(
        unique,
        niche=niche,
        title_key="title",
        content_key="text",
        score_key="points",
        min_score=10,           # min 10 HN points = real community validation
        date_key="created_at",
        max_years=3,
        min_relevance=0.1,      # HN titles are short, so lower threshold
        limit=15,
    )


async def _fetch_hn(client: httpx.AsyncClient, query: str) -> list[dict]:
    params = {
        "query": query,
        "tags": "(story,comment)",
        "hitsPerPage": 15,
        "numericFilters": "points>9",   # enforce min 10 points at API level
    }
    try:
        r = await client.get(HN_SEARCH_URL, params=params)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        return [
            {
                "title": h.get("title") or h.get("comment_text", "")[:100],
                "text": (h.get("story_text") or h.get("comment_text") or "")[:400],
                "points": h.get("points", 0),
                "url": h.get("url", f"https://news.ycombinator.com/item?id={h.get('objectID')}"),
                "created_at": h.get("created_at", ""),
                "source": "Hacker News",
                "objectID": h.get("objectID"),
            }
            for h in hits
            if h.get("title") or h.get("comment_text")
        ]
    except Exception:
        return []
