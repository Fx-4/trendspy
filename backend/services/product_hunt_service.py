"""
Product Hunt API service — free tier, needs API key.
Returns competitor products with vote counts, taglines, reviews.
Perfect for the COMPETITOR GAPS section.

Setup (5 minutes, no CC):
1. Go to https://www.producthunt.com/v2/oauth/applications
2. Create a new application (type: Client Only)
3. Copy the "API Key" (Developer Token)
4. Add to backend/.env: PRODUCT_HUNT_API_KEY=your_token_here
"""
import httpx
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

PH_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"
PH_API_KEY = os.getenv("PRODUCT_HUNT_API_KEY", "")

_SEARCH_QUERY = """
query SearchPosts($query: String!, $first: Int!) {
  posts(first: $first, query: $query, order: VOTES) {
    edges {
      node {
        name
        tagline
        description
        votesCount
        reviewsCount
        reviewsRating
        website
        topics {
          edges {
            node { name }
          }
        }
        comments(first: 3) {
          edges {
            node { body }
          }
        }
      }
    }
  }
}
"""


async def search_product_hunt(niche: str) -> list[dict]:
    """Search Product Hunt for products related to the niche."""
    if not PH_API_KEY:
        return []  # Gracefully skip if API key not set

    headers = {
        "Authorization": f"Bearer {PH_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "query": _SEARCH_QUERY,
        "variables": {"query": niche, "first": 10},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(PH_GRAPHQL_URL, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        edges = data.get("data", {}).get("posts", {}).get("edges", [])
        results = []
        for edge in edges:
            node = edge.get("node", {})
            if not node.get("name"):
                continue

            # Extract top comments (user feedback)
            comments = [
                c["node"]["body"][:200]
                for c in node.get("comments", {}).get("edges", [])
                if c.get("node", {}).get("body")
            ]

            results.append({
                "name": node.get("name", ""),
                "tagline": node.get("tagline", ""),
                "description": (node.get("description") or "")[:400],
                "votes": node.get("votesCount", 0),
                "reviews": node.get("reviewsCount", 0),
                "rating": node.get("reviewsRating", 0),
                "url": node.get("website", ""),
                "top_comments": comments,
                "source": "Product Hunt",
            })

        return sorted(results, key=lambda x: x["votes"], reverse=True)[:8]

    except Exception:
        return []
