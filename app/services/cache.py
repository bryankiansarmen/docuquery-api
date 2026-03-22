import redis, hashlib, json, os
from loguru import logger

REDIS_HOST = os.getenv("REDIS_HOST")

try:
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
    r.ping()
except Exception as e:
    logger.warning(f"Could not connect to Redis at {REDIS_HOST}: {e}. Caching disabled.")
    r = None

def create_answer_key(question: str, file_name: str) -> str:
    """Generate a unique cache key for a question and document."""
    return hashlib.sha256(f"{question}{file_name}".encode()).hexdigest()

def get_answer_cache(key: str):
    """Retrieve cached answer from Redis."""
    if not r: return None
    try:
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception as e:
        logger.error(f"Redis cache read error: {e}")
        return None

def save_answer_cache(key: str, value: dict):
    """Store answer in Redis with 1 hour expiration."""
    if not r: return
    try:
        r.setex(key, 3600, json.dumps(value))
    except Exception as e:
        logger.error(f"Redis cache write error: {e}")

def get_doc_meta(doc_id: str):
    """Retrieve document metadata from Redis by hash."""
    if not r: return None
    try:
        val = r.get(f"doc:{doc_id}")
        return json.loads(val) if val else None
    except Exception as e:
        logger.warning(f"Redis meta read error: {e}")
        return None

def save_doc_meta(doc_id: str, meta: dict):
    """Save document metadata to Redis."""
    if not r: return
    try:
        r.set(f"doc:{doc_id}", json.dumps(meta))
    except Exception as e:
        logger.error(f"Redis meta write error: {e}")
