"""
Stack Exchange API service — free, no auth required for basic usage.
Searches across multiple SE communities for relevant Q&A.
Quality filter: min score 3, must have answers, published ≤3 years ago.
Questions with high votes = real pain points verified by the community.
"""
import httpx
import asyncio
import html
from services.data_quality import filter_items

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
        "pagesize": 10,
        "filter": "!9_bDDzB48",  # include body excerpt
        "min": 3,                 # minimum score of 3 — community-validated questions only
    }
    try:
        r = await client.get(f"{SE_API}/search/advanced", params=params, timeout=8.0)
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        return [
            {
                "title": html.unescape(i.get("title", "")),
                "body": html.unescape((i.get("body", "") or "")[:400]),
                "score": i.get("score", 0),
                "answer_count": i.get("answer_count", 0),
                "is_answered": i.get("is_answered", False),
                "creation_date": i.get("creation_date"),   # Unix timestamp
                "url": i.get("link", ""),
                "source": f"Stack Exchange ({site})",
                "site": site,
            }
            for i in items
            if i.get("score", 0) >= 3            # minimum 3 upvotes
            and i.get("answer_count", 0) >= 1    # must have at least 1 answer (verified real problem)
            and (i.get("title") or "")
        ]
    except Exception:
        return []


def _se_is_recent(unix_ts, max_years: int = 3) -> bool:
    """Stack Exchange uses Unix timestamps, not ISO dates."""
    if not unix_ts:
        return True
    try:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - dt).days / 365 <= max_years
    except Exception:
        return True


async def search_stackexchange(niche: str) -> list[dict]:
    """
    Search Stack Exchange communities for questions related to the niche.
    Only returns questions with score ≥3 AND at least 1 answer.
    High votes + answers = real, verified pain points.
    """
    queries = [
        niche,
        f"{niche} problems",
        f"{niche} alternatives",
    ]

    async with httpx.AsyncClient() as client:
        tasks = []
        for site in _SE_SITES[:3]:
            for q in queries[:2]:
                tasks.append(_fetch_questions(client, q, site))
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items = []
    for r in results:
        if isinstance(r, list):
            all_items.extend(r)

    # Deduplicate by URL, filter recency, sort by vote score
    seen = set()
    unique = []
    for item in sorted(all_items, key=lambda x: x["score"], reverse=True):
        if item["url"] not in seen and _se_is_recent(item.get("creation_date"), max_years=3):
            seen.add(item["url"])
            unique.append(item)

    # Apply quality + relevance filter
    return filter_items(
        unique,
        niche=niche,
        title_key="title",
        content_key="body",
        score_key="score",
        min_score=3,
        min_relevance=0.15,
        limit=12,
    )
