import httpx
import os
from dotenv import load_dotenv

load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY", "")
EXA_URL = "https://api.exa.ai/search"


async def search_exa(niche: str) -> list[dict]:
    """Search web using Exa neural search API."""
    if not EXA_API_KEY:
        return []

    headers = {"x-api-key": EXA_API_KEY, "Content-Type": "application/json"}
    payload = {
        "query": f"{niche} market feedback problems user reviews",
        "numResults": 5,
        "contents": {"text": True},
        "useAutoprompt": True,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(EXA_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "text": (r.get("text") or "")[:600],
                    "source": "neural_web",
                }
                for r in results
            ]
        except Exception:
            return []
