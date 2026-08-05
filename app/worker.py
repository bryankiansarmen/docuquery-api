import base64, os, threading, time
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from app.db.redis import redis_client
from app.services.stream import (
    STREAM_KEY,
    CONSUMER_GROUP,
    CONSUMER_NAME,
    save_job_status,
    create_consumer_group,
)
from app.services.pdf import extract_text_from_pdf, chunk_text
from app.services.vector import store_document_chunks
from app.services.document import save_document_metadata_sync
from app.services.cache import save_document_metadata as save_redis_metadata
from app.models.schemas import DocumentMetadata, JobStatus

MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "2"))
PENDING_RECLAIM_MIN_IDLE_MS = 30000


def process_job(message_id: str, data: dict) -> bool:
    job_id = data["job_id"]
    file_name = data["file_name"]
    document_id = data["document_id"]
    tenant_id = data.get("tenant_id", "default")

    logger.info(f"Processing job {job_id} for {file_name}")
    save_job_status(job_id, JobStatus.processing)

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            file_bytes = base64.b64decode(data["file_bytes"])
            content, page_count = extract_text_from_pdf(file_bytes)
            if not content or not content.strip():
                raise ValueError("PDF contains no extractable text")
            chunks = chunk_text(content)
            if not chunks:
                raise ValueError("No text chunks could be extracted from PDF")

            if not store_document_chunks(chunks, file_name, document_id, tenant_id):
                raise RuntimeError("Failed to store document chunks")

            metadata = DocumentMetadata(
                document_id=document_id,
                file_name=file_name,
                page_count=page_count,
                chunk_count=len(chunks),
                user_id=tenant_id,
            )
            if not save_document_metadata_sync(metadata):
                raise RuntimeError("Failed to save document metadata")

            # Persist to Redis too so de-dup + active-document recovery survive restarts.
            save_redis_metadata(document_id, metadata.model_dump(), tenant_id)

            save_job_status(job_id, JobStatus.completed, f"Processed {len(chunks)} chunks")
            logger.info(f"Job {job_id} completed")
            redis_client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
            return True
        except Exception as e:
            last_error = e
            logger.error(f"Job {job_id} attempt {attempt}/{MAX_ATTEMPTS} failed: {e}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 ** attempt)

    save_job_status(job_id, JobStatus.failed, str(last_error))
    redis_client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
    logger.error(f"Job {job_id} permanently failed: {last_error}")
    return False


def reclaim_pending():
    """Reclaim messages left pending by a previous (crashed) worker."""
    if not redis_client:
        return
    try:
        pending = redis_client.xpending_range(
            STREAM_KEY, CONSUMER_GROUP, min="-", max="+", count=100
        )
        pending_ids = [entry["id"] for entry in pending]
        if not pending_ids:
            return
        claimed = redis_client.xclaim(
            STREAM_KEY, CONSUMER_GROUP, CONSUMER_NAME,
            PENDING_RECLAIM_MIN_IDLE_MS, pending_ids,
        )
        for entry in claimed:
            message_id, fields = entry[0], entry[1]
            process_job(message_id, fields)
        logger.info(f"Reclaimed {len(claimed)} idle pending jobs")
    except Exception as e:
        logger.warning(f"Could not reclaim pending jobs: {e}")


def run_worker(stop_event: threading.Event = None):
    logger.info("Worker started, waiting for jobs...")
    create_consumer_group()
    reclaim_pending()

    with ThreadPoolExecutor(max_workers=WORKER_CONCURRENCY) as executor:
        futures = []
        while not (stop_event and stop_event.is_set()):
            try:
                messages = redis_client.xreadgroup(
                    groupname=CONSUMER_GROUP,
                    consumername=CONSUMER_NAME,
                    streams={STREAM_KEY: ">"},
                    count=WORKER_CONCURRENCY,
                    block=5000,
                )

                if not messages:
                    futures = [f for f in futures if not f.done()]
                    # Avoid a tight spin while idle.
                    time.sleep(0.2 if not futures else 0.1)
                    continue

                for _stream, entries in messages:
                    for message_id, data in entries:
                        futures.append(executor.submit(process_job, message_id, data))
                futures = [f for f in futures if not f.done()]
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(2)


if __name__ == "__main__":
    run_worker()