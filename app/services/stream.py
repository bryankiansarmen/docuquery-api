from app.db.redis import redis_client
from loguru import logger
import json, uuid

STREAM_KEY = "docquery:upload_jobs"
CONSUMER_GROUP = "upload_worker"
CONSUMER_NAME = "worker_1"

def publish_upload_job(document_id: str, file_name: str, temp_path: str) -> str:
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    
    job_id = str(uuid.uuid4())
    redis_client.xadd(STREAM_KEY, {
        "job_id": job_id,
        "document_id": document_id,
        "file_name": file_name,
        "temp_path": temp_path
    })

    logger.info(f"Published upload job: {job_id} for {file_name}")

    return job_id

def create_consumer_group():
    if not redis_client:
        logger.warning("Redis client not initialized, skipping consumer group creation")
        return

    try:
        redis_client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(f"Created consumer group: {CONSUMER_GROUP}")
    except Exception as e:
        if "BUSYGROUP" in str(e):
            logger.info(f"Consumer group {CONSUMER_GROUP} already exists")
        else:
            logger.error(f"Failed to create consumer group: {e}")
            raise

def get_job_status(job_id: str) -> dict | None:
    if not redis_client:
        return None

    value = redis_client.get(f"job:{job_id}")

    return json.loads(value) if value else None

def save_job_status(job_id: str, status: str, message: str = ""):
    if not redis_client:
        return

    redis_client.setex(
        f"job:{job_id}",
        86400, # 24hr TTL
        json.dumps({
            "job_id": job_id,
            "status": status,
            "message": message
        })
    )