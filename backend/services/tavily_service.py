import httpx
import os
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_URL = "https://api.tavily.com/search"


async def search_tavily(niche: str) -> list[dict]:
    """Search web using Tavily AI search API."""
    if not TAVILY_API_KEY:
        return []

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": f"{niche} alternatives competitors pricing user reviews",
        "search_depth": "basic",
        "max_results": 5,
        "include_raw_content": False,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(TAVILY_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:600],
                    "score": r.get("score", 0),
                    "source": "web",
                }
                for r in results
            ]
        except Exception:
            return []
