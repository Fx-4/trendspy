import httpx
import os
from dotenv import load_dotenv

load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY", "")
EXA_URL = "https://api.exa.ai/search"


async def _exa_query(client: httpx.AsyncClient, headers: dict, query: str, num: int = 5) -> list[dict]:
    payload = {
        "query": query,
        "numResults": num,
        "contents": {"text": True},
        "useAutoprompt": True,
    }
    try:
        response = await client.post(EXA_URL, json=payload, headers=headers)
        response.raise_for_status()
        results = response.json().get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "text": (r.get("text") or "")[:700],
                "source": "Exa",
            }
            for r in results
            if (r.get("text") or "").strip()
        ]
    except Exception:
        return []


async def search_exa(niche: str) -> list[dict]:
    """Search web using Exa neural search API — 2 targeted queries."""
    if not EXA_API_KEY:
        return []

    headers = {"x-api-key": EXA_API_KEY, "Content-Type": "application/json"}

    import asyncio
    async with httpx.AsyncClient(timeout=15.0) as client:
        complaints, pricing = await asyncio.gather(
            _exa_query(client, headers, f"frustrated with {niche} tool — here is why I switched or stopped using it", 5),
            _exa_query(client, headers, f"{niche} app pricing breakdown Calendly Acuity Cal.com monthly cost", 4),
        )

    seen = set()
    combined = []
    for item in complaints + pricing:
        if item["url"] not in seen:
            seen.add(item["url"])
            combined.append(item)

    return combined[:10]
