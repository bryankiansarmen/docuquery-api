import base64, json, os, uuid
from app.db.redis import redis_client
from loguru import logger

STREAM_KEY = "docquery:upload_jobs"
CONSUMER_GROUP = "upload_worker"
# Unique consumer name per process so multiple workers can share the group.
CONSUMER_NAME = f"worker_{os.getpid()}_{uuid.uuid4().hex[:6]}"

def publish_upload_job(
    document_id: str,
    file_name: str,
    file_bytes: bytes,
    tenant_id: str | None = None,
) -> str:
    """Publish a PDF processing job with the file bytes embedded in the stream.

    The bytes are base64-encoded so the job is portable across hosts (e.g. a
    separate worker container with no shared filesystem). A 'pending' status is
    written immediately so status polling never 404s right after upload.
    """
    if not redis_client:
        raise RuntimeError("Redis client not initialized")

    job_id = str(uuid.uuid4())
    redis_client.xadd(STREAM_KEY, {
        "job_id": job_id,
        "document_id": document_id,
        "file_name": file_name,
        "file_bytes": base64.b64encode(file_bytes).decode("ascii"),
        "tenant_id": tenant_id or "default",
    })

    save_job_status(job_id, "pending", "Queued for processing")
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
