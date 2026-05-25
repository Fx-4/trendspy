"""
Utility to delete cached briefs and/or rate-limit counters from Upstash Redis.

Usage:
  python clear_cache.py                         # clear ALL brief: cache keys
  python clear_cache.py "freelance scheduling"  # clear one specific niche
  python clear_cache.py --rates                 # clear ALL rate: limit keys
  python clear_cache.py --rates 127.0.0.1       # clear rate limit for one IP
"""
import hashlib
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from upstash_redis import Redis

redis = Redis(
    url=os.getenv("UPSTASH_REDIS_REST_URL", ""),
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
)

args = sys.argv[1:]

# ── Rate-limit clearing ────────────────────────────────────────────────────────
if args and args[0] == "--rates":
    ip = args[1] if len(args) > 1 else None
    if ip:
        key = f"rate:{ip}"
        deleted = redis.delete(key)
        print(f"Rate key : {key}")
        print(f"Deleted  : {deleted} key(s)")
    else:
        keys = redis.keys("rate:*")
        if keys:
            deleted = redis.delete(*keys)
            print(f"Deleted {deleted} rate-limit key(s):")
            for k in keys:
                print(f"  - {k}")
        else:
            print("No rate-limit keys found.")

# ── Brief cache clearing ───────────────────────────────────────────────────────
elif args:
    niche = " ".join(args)
    key = f"brief:{hashlib.md5(niche.lower().strip().encode()).hexdigest()}"
    deleted = redis.delete(key)
    print(f"Niche   : '{niche}'")
    print(f"Key     : {key}")
    print(f"Deleted : {deleted} key(s)")

else:
    keys = redis.keys("brief:*")
    if keys:
        deleted = redis.delete(*keys)
        print(f"Deleted {deleted} cached brief(s):")
        for k in keys:
            print(f"  - {k}")
    else:
        print("No cached briefs found.")
