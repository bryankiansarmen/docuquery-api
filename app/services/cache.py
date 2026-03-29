import hashlib, json
from loguru import logger
from app.db.redis import redis_client

def create_answer_key(question: str, file_name: str) -> str:
    return hashlib.sha256(f"{question}{file_name}".encode()).hexdigest()

def get_answer_cache(key: str):
    if not redis_client: return None
    try:
        val = redis_client.get(key)
        return json.loads(val) if val else None
    except Exception as e:
        logger.error(f"Redis cache read error: {e}")
        return None

def save_answer_cache(key: str, value: dict):
    if not redis_client: return
    try:
        redis_client.setex(key, 3600, json.dumps(value))
    except Exception as e:
        logger.error(f"Redis cache write error: {e}")

def get_document_metadata(document_id: str) -> dict | None:
    if not redis_client: return None
    try:
        val = redis_client.get(f"document:{document_id}")
        return json.loads(val) if val else None
    except Exception as e:
        logger.warning(f"Redis document metadata read error: {e}")
        return None

def save_document_metadata(document_id: str, meta: dict):
    if not redis_client: return
    try:
        redis_client.set(f"document:{document_id}", json.dumps(meta))
        redis_client.set("active_document", json.dumps(meta))
        logger.debug(f"Saved document metadata to Redis: {document_id}")
    except Exception as e:
        logger.error(f"Redis document metadata write error: {e}")

def get_active_document() -> dict | None:
    if not redis_client: return None
    try:
        val = redis_client.get("active_document")
        return json.loads(val) if val else None
    except Exception as e:
        logger.warning(f"Redis active document read error: {e}")
        return None
