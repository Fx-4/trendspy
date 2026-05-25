import httpx
import asyncio
import os
import time
from dotenv import load_dotenv

load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "")

# Token cache
_token_cache = {"token": None, "expires_at": 0}

# Subreddits per niche keyword
NICHE_SUBREDDIT_MAP = {
    "freelance": ["freelance", "freelancing", "digitalnomad"],
    "scheduling": ["freelance", "productivity", "smallbusiness"],
    "ai": ["MachineLearning", "artificial", "SaaS", "ChatGPT"],
    "writing": ["writing", "freelance", "content_marketing"],
    "legal": ["legaladvice", "LegalTech", "lawyers"],
    "fitness": ["fitness", "personaltraining", "Entrepreneur"],
    "ecommerce": ["ecommerce", "shopify", "FulfillmentByAmazon"],
    "saas": ["SaaS", "startups", "microsaas", "entrepreneur"],
    "health": ["HealthTech", "medicine", "startups"],
    "education": ["edtech", "learnprogramming", "Entrepreneur"],
    "finance": ["personalfinance", "fintech", "startups"],
    "remote": ["remotework", "digitalnomad", "WorkOnline"],
    "pet": ["pets", "dogs", "cats"],
    "food": ["restaurantowners", "foodservice", "Entrepreneur"],
    "travel": ["solotravel", "digitalnomad", "backpacking"],
    "productivity": ["productivity", "getdisciplined", "Entrepreneur"],
    "marketing": ["marketing", "socialmedia", "digital_marketing"],
    "developer": ["webdev", "programming", "SaaS", "cscareerquestions"],
}

FALLBACK_SUBREDDITS = ["entrepreneur", "startups", "SaaS"]


def get_relevant_subreddits(niche: str) -> list[str]:
    niche_lower = niche.lower()
    subreddits = set()
    for keyword, subs in NICHE_SUBREDDIT_MAP.items():
        if keyword in niche_lower:
            subreddits.update(subs)
    if not subreddits:
        subreddits.update(FALLBACK_SUBREDDITS)
    else:
        subreddits.update(FALLBACK_SUBREDDITS[:2])
    return list(subreddits)[:6]


async def get_oauth_token() -> str | None:
    """Get Reddit OAuth token using client_credentials (app-only auth)."""
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return None

    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    ua = f"TrendSpy:v1.0 (by /u/{REDDIT_USERNAME})" if REDDIT_USERNAME else "TrendSpy:v1.0 (hackathon app)"

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": ua},
                timeout=10.0,
            )
            r.raise_for_status()
            data = r.json()
            token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            if token:
                _token_cache["token"] = token
                _token_cache["expires_at"] = now + expires_in
                return token
    except Exception:
        pass
    return None


async def search_subreddit_oauth(
    client: httpx.AsyncClient,
    subreddit: str,
    query: str,
    token: str,
    username: str,
) -> list[dict]:
    """Search a subreddit using OAuth."""
    ua = f"TrendSpy:v1.0 (by /u/{username})" if username else "TrendSpy:v1.0"
    url = f"https://oauth.reddit.com/r/{subreddit}/search"
    params = {"q": query, "sort": "top", "t": "year", "limit": 15, "restrict_sr": "true"}
    headers = {"Authorization": f"bearer {token}", "User-Agent": ua}
    try:
        r = await client.get(url, params=params, headers=headers, timeout=8.0)
        if r.status_code in (429, 403):
            return []
        r.raise_for_status()
        posts = r.json().get("data", {}).get("children", [])
        return [
            {
                "title": p["data"].get("title", ""),
                "selftext": p["data"].get("selftext", "")[:400],
                "score": p["data"].get("score", 0),
                "subreddit": p["data"].get("subreddit", subreddit),
                "url": p["data"].get("url", ""),
                "num_comments": p["data"].get("num_comments", 0),
            }
            for p in posts
            if p["data"].get("score", 0) > 1
        ]
    except Exception:
        return []


async def search_reddit(niche: str) -> list[dict]:
    """Search Reddit. Uses OAuth if credentials set, else returns empty."""
    token = await get_oauth_token()
    if not token:
        return []

    subreddits = get_relevant_subreddits(niche)
    query = f"{niche} problems alternatives experience"

    async with httpx.AsyncClient() as client:
        tasks = [
            search_subreddit_oauth(client, sub, query, token, REDDIT_USERNAME)
            for sub in subreddits
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_posts = []
    for r in results:
        if isinstance(r, list):
            all_posts.extend(r)

    # Sort by score, deduplicate
    seen = set()
    unique = []
    for p in sorted(all_posts, key=lambda x: x["score"], reverse=True):
        key = p["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique[:20]
