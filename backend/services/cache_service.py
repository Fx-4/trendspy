from upstash_redis import Redis
from dotenv import load_dotenv
import os
import hashlib

load_dotenv()

redis = Redis(
    url=os.getenv("UPSTASH_REDIS_REST_URL", ""),
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
)


def make_cache_key(niche: str) -> str:
    normalized = niche.lower().strip()
    return f"brief:{hashlib.md5(normalized.encode()).hexdigest()}"


def make_rate_key(ip: str) -> str:
    return f"rate:{ip}"


async def get_cached(niche: str) -> str | None:
    try:
        key = make_cache_key(niche)
        return redis.get(key)
    except Exception:
        return None


async def set_cache(niche: str, value: str, ttl: int = 3600) -> None:
    try:
        key = make_cache_key(niche)
        redis.set(key, value, ex=ttl)
    except Exception:
        pass  # Cache failures should not break the app


async def check_rate_limit(ip: str, max_requests: int = 10) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    try:
        key = make_rate_key(ip)
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, 3600)  # 1 hour window
        return count <= max_requests
    except Exception:
        return True  # Allow on cache failure
