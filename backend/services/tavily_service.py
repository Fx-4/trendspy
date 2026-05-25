import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_URL = "https://api.tavily.com/search"


async def _tavily_search(client: httpx.AsyncClient, query: str, depth: str = "basic", max_results: int = 8) -> list[dict]:
    if not TAVILY_API_KEY:
        return []
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": depth,
        "max_results": max_results,
        "include_raw_content": False,
    }
    try:
        response = await client.post(TAVILY_URL, json=payload)
        response.raise_for_status()
        results = response.json().get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:700],
                "score": r.get("score", 0),
                "source": "Tavily",
            }
            for r in results
            if r.get("content")
        ]
    except Exception:
        return []


async def search_tavily(niche: str) -> list[dict]:
    """Search web using Tavily AI search API — 3 targeted queries in parallel."""
    if not TAVILY_API_KEY:
        return []

    queries = [
        # User complaints and honest reviews
        (f"{niche} problems complaints limitations honest review cons", "basic", 8),
        # Specific pricing — advanced scrapes actual pricing pages
        (f"{niche} software pricing plans how much cost per month", "advanced", 5),
        # What users wish the product had / what's missing
        (f"why freelancers hate {niche} tools what is missing feature requests", "basic", 6),
    ]

    async with httpx.AsyncClient(timeout=20.0) as client:
        tasks = [_tavily_search(client, q, depth, n) for q, depth, n in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_results = []
    seen_urls = set()
    for r in results:
        if isinstance(r, list):
            for item in r:
                if item["url"] not in seen_urls and item["content"].strip():
                    seen_urls.add(item["url"])
                    all_results.append(item)

    # Sort by Tavily relevance score, return top 15
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return all_results[:15]
