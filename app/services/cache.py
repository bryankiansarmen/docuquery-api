import redis, hashlib, json, os
from loguru import logger

REDIS_HOST = os.getenv("REDIS_HOST")

try:
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
    r.ping()
except Exception as e:
    logger.warning(f"Could not connect to Redis at {REDIS_HOST}: {e}. Caching disabled.")
    r = None

def make_key(question: str, filename: str) -> str:
    """Generate a unique cache key for a question and document."""
    return hashlib.md5(f"{question}{filename}".encode()).hexdigest()

def get_cache(key: str):
    """Retrieve cached answer from Redis."""
    if not r: return None
    try:
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception as e:
        logger.error(f"Redis read error: {e}")
        return None

def set_cache(key: str, value: dict):
    """Store answer in Redis with 1 hour expiration."""
    if not r: return
    try:
        r.setex(key, 3600, json.dumps(value))
    except Exception as e:
        logger.error(f"Redis write error: {e}")
