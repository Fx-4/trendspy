"""
Stack Exchange API service — free, no auth required for basic usage.
Searches across multiple SE communities for relevant Q&A.
Questions with high votes = real pain points from real users.
"""
import httpx
import asyncio
import html

SE_API = "https://api.stackexchange.com/2.3"

# Most relevant SE communities for startup/product/SaaS niches
# Full list: https://stackexchange.com/sites
_SE_SITES = [
    "startups",          # Startups SE — founders, product, business model questions
    "softwarerecs",      # Software Recommendations — "I need a tool that does X"
    "webapps",           # Web Applications — tool comparisons and usage
    "productivity",      # Productivity SE — workflow pain points
]


async def _fetch_questions(
    client: httpx.AsyncClient, query: str, site: str
) -> list[dict]:
    params = {
        "q": query,
        "site": site,
        "order": "desc",
        "sort": "votes",
        "pagesize": 8,
        "filter": "!9_bDDzB48",  # include body excerpt
    }
    try:
        r = await client.get(f"{SE_API}/search/advanced", params=params, timeout=8.0)
        r.raise_for_status()
        items = r.json().get("items", [])
        return [
            {
                "title": html.unescape(i.get("title", "")),
                "body": html.unescape((i.get("body", "") or "")[:400]),
                "score": i.get("score", 0),
                "answer_count": i.get("answer_count", 0),
                "url": i.get("link", ""),
                "source": f"Stack Exchange ({site})",
                "site": site,
            }
            for i in items
            if i.get("score", 0) >= 1 and (i.get("title") or "")
        ]
    except Exception:
        return []


async def search_stackexchange(niche: str) -> list[dict]:
    """
    Search Stack Exchange communities for questions related to the niche.
    Returns high-voted questions — each question = a real pain point.
    """
    queries = [
        niche,
        f"{niche} problems",
        f"{niche} alternatives",
    ]

    async with httpx.AsyncClient() as client:
        tasks = []
        for site in _SE_SITES[:3]:          # limit to 3 sites to avoid hammering
            for q in queries[:2]:            # 2 queries per site
                tasks.append(_fetch_questions(client, q, site))
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items = []
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)

    # Deduplicate by URL, sort by vote score
    seen = set()
    unique = []
    for item in sorted(all_items, key=lambda x: x["score"], reverse=True):
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)

    return unique[:12]
