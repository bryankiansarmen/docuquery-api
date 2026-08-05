import hashlib, json
from datetime import datetime, date
from loguru import logger
from app.db.redis import redis_client
from app.services.store import DEFAULT_TENANT


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


def _dumps(value) -> str:
    return json.dumps(value, default=_json_default)


def create_answer_key(question: str, file_name: str, tenant_id: str | None = None) -> str:
    return hashlib.sha256(f"{question}{file_name}{tenant_id or DEFAULT_TENANT}".encode()).hexdigest()

def get_answer_cache(key: str):
    if not redis_client: return None
    try:
        value = redis_client.get(key)
        return json.loads(value) if value else None
    except Exception as e:
        logger.error(f"Redis cache read error: {e}")
        return None

def save_answer_cache(key: str, value: dict):
    if not redis_client: return
    try:
        redis_client.setex(key, 3600, _dumps(value))
    except Exception as e:
        logger.error(f"Redis cache write error: {e}")

def get_document_metadata(document_id: str, tenant_id: str | None = None) -> dict | None:
    if not redis_client: return None
    try:
        value = redis_client.get(f"document:{tenant_id or DEFAULT_TENANT}:{document_id}")
        return json.loads(value) if value else None
    except Exception as e:
        logger.warning(f"Redis document metadata read error: {e}")
        return None

def save_document_metadata(document_id: str, meta: dict, tenant_id: str | None = None):
    if not redis_client: return
    try:
        tenant = tenant_id or DEFAULT_TENANT
        redis_client.set(f"document:{tenant}:{document_id}", _dumps(meta))
        redis_client.set(f"active_document:{tenant}", _dumps(meta))
        logger.debug(f"Saved document metadata to Redis: {document_id}")
    except Exception as e:
        logger.error(f"Redis document metadata write error: {e}")

def get_active_document(tenant_id: str | None = None) -> dict | None:
    if not redis_client: return None
    try:
        value = redis_client.get(f"active_document:{tenant_id or DEFAULT_TENANT}")
        return json.loads(value) if value else None
    except Exception as e:
        logger.warning(f"Redis active document read error: {e}")
        return None
