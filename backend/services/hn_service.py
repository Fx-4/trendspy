"""
Hacker News API service — free, no auth needed.
Great for tech/SaaS/startup niches (indie makers, founders).
"""
import httpx
import asyncio

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


async def search_hn(niche: str) -> list[dict]:
    """Search Hacker News via Algolia API (completely free, no auth)."""
    queries = [
        f"{niche} pain points",
        f"{niche} alternatives",
        f"Ask HN: {niche}",
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

    return unique[:15]


async def _fetch_hn(client: httpx.AsyncClient, query: str) -> list[dict]:
    params = {
        "query": query,
        "tags": "(story,comment)",
        "hitsPerPage": 10,
        "numericFilters": "points>5",
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
                "source": "HackerNews",
                "objectID": h.get("objectID"),
            }
            for h in hits
            if h.get("title") or h.get("comment_text")
        ]
    except Exception:
        return []
