import time, os, threading
from loguru import logger
from app.db.redis import redis_client
from app.services.stream import STREAM_KEY, CONSUMER_GROUP, CONSUMER_NAME, save_job_status, create_consumer_group
from app.services.pdf import extract_text_from_pdf, chunk_text
from app.services.vector import store_document_chunks
from app.services.document import save_document_metadata_sync
from app.clients.gemini import gemini_client
from app.models.schemas import DocumentMetadata, JobStatus

def process_job(message_id: str, data: dict):
    job_id = data["job_id"]
    file_name = data["file_name"]
    temp_path = data["temp_path"]
    document_id = data["document_id"]

    logger.info(f"Processing job {job_id} for {file_name}")
    save_job_status(job_id, JobStatus.processing)

    try:
        with open(temp_path, "rb") as f:
            file_bytes = f.read()

        content, page_count = extract_text_from_pdf(file_bytes)
        chunks = chunk_text(content)
        store_document_chunks(chunks, file_name, gemini_client, document_id)

        metadata = DocumentMetadata(
            document_id=document_id,
            file_name=file_name,
            page_count=page_count,
            chunk_count=len(chunks)
        )
        save_document_metadata_sync(metadata)

        save_job_status(job_id, JobStatus.completed, f"Processed {len(chunks)} chunks")
        logger.info(f"Job {job_id} completed")

        redis_client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)

        os.remove(temp_path)

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        save_job_status(job_id, JobStatus.failed, str(e))
        redis_client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)


def run_worker(stop_event: threading.Event = None):
    logger.info("Worker started, waiting for jobs...")
    create_consumer_group()

    while not (stop_event and stop_event.is_set()):
        try:
            messages = redis_client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_KEY: ">"},
                count=1,
                block=5000
            )

            if not messages:
                continue

            for stream, entries in messages:
                for message_id, data in entries:
                    process_job(message_id, data)

        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    run_worker()