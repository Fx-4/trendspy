from upstash_redis import Redis
from dotenv import load_dotenv
import os
import hashlib

load_dotenv()

redis = Redis(
    url=os.getenv("UPSTASH_REDIS_REST_URL", ""),
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
)

_IS_DEV = os.getenv("APP_ENV", "development").lower() == "development"

# IPs that are always localhost — never rate-limit these in dev
_LOCAL_IPS = {"127.0.0.1", "::1", "localhost"}


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


async def check_rate_limit(ip: str, max_requests: int = 30) -> bool:
    """Returns True if request is allowed, False if rate limited.

    Localhost is never rate-limited in development mode.
    Production limit is 30 requests/hour per IP.
    """
    # Never rate-limit local development traffic
    if _IS_DEV and ip in _LOCAL_IPS:
        return True

    try:
        key = make_rate_key(ip)
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, 3600)  # 1 hour window
        return count <= max_requests
    except Exception:
        return True  # Allow on cache failure


async def clear_rate_limit(ip: str) -> int:
    """Delete the rate-limit counter for an IP. Returns 1 if deleted, 0 if not found."""
    try:
        return redis.delete(make_rate_key(ip))
    except Exception:
        return 0
