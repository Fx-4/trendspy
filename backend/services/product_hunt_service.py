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
            name = node.get("name", "").strip()
            description = (node.get("description") or "").strip()
            votes = node.get("votesCount", 0)
            website = node.get("website", "").strip()

            # Quality gates for Product Hunt data:
            if not name:
                continue
            if votes < 15:                    # min 15 votes = real community interest
                continue
            if len(description) < 30:         # must have a real description
                continue
            if not website:                   # must be a real product with a URL
                continue

            # Extract top comments (user feedback = real opinions)
            comments = [
                c["node"]["body"][:200]
                for c in node.get("comments", {}).get("edges", [])
                if c.get("node", {}).get("body")
                and len(c["node"]["body"]) > 30     # skip very short comments
            ]

            results.append({
                "name": name,
                "tagline": node.get("tagline", ""),
                "description": description[:400],
                "votes": votes,
                "reviews": node.get("reviewsCount", 0),
                "rating": node.get("reviewsRating", 0),
                "url": website,
                "top_comments": comments[:3],
                "source": "Product Hunt",
            })

        # Sort by votes (= community validation strength) and return top results
        return sorted(results, key=lambda x: x["votes"], reverse=True)[:8]

    except Exception:
        return []
