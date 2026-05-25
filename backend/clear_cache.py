"""
Quick utility to delete a cached brief from Upstash Redis.
Usage: python clear_cache.py "freelance scheduling app"
       python clear_cache.py  (clears ALL brief: keys)
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

if len(sys.argv) > 1:
    # Clear a specific niche
    niche = " ".join(sys.argv[1:])
    key = f"brief:{hashlib.md5(niche.lower().strip().encode()).hexdigest()}"
    deleted = redis.delete(key)
    print(f"Niche   : '{niche}'")
    print(f"Key     : {key}")
    print(f"Deleted : {deleted} key(s)")
else:
    # Clear ALL brief: keys
    keys = redis.keys("brief:*")
    if keys:
        deleted = redis.delete(*keys)
        print(f"Deleted {deleted} cached brief(s):")
        for k in keys:
            print(f"  - {k}")
    else:
        print("No cached briefs found.")
