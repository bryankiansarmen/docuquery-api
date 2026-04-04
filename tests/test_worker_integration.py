import pytest
import threading
import time
from unittest.mock import MagicMock, patch
from app.worker import run_worker
from app.models.schemas import JobStatus

@pytest.fixture
def mock_redis_stream():
    messages = []
    job_statuses = {}
    
    def xadd(_, fields, **kwargs):
        msg_id = f"{int(time.time()*1000)}-0"
        messages.append((msg_id, fields))
        return msg_id
        
    def xreadgroup(streams, *args, **kwargs):
        if not messages:
            return []
        msg_id, data = messages.pop(0)
        stream_name = list(streams.keys())[0]
        return [[stream_name, [(msg_id, data)]]]

    def setex(name, _, value):
        job_statuses[name] = value
        
    def get(name):
        return job_statuses.get(name)

    mock = MagicMock()
    mock.xadd.side_effect = xadd
    mock.xreadgroup.side_effect = xreadgroup
    mock.setex.side_effect = setex
    mock.get.side_effect = get
    return mock

def test_worker_integration_flow(client, mocker, mock_redis_stream):
    mocker.patch("app.services.stream.redis_client", mock_redis_stream)
    mocker.patch("app.worker.redis_client", mock_redis_stream)
    
    mocker.patch("app.worker.extract_text_from_pdf", return_value=("Mocked text", 2))
    mocker.patch("app.worker.chunk_text", return_value=["chunk1", "chunk2"])
    mocker.patch("app.worker.store_document_chunks")
    mocker.patch("app.worker.save_document_metadata_sync")
    mocker.patch("app.worker.index_chunks")
    
    mocker.patch("builtins.open", mocker.mock_open(read_data=b"fake pdf"))
    mocker.patch("os.remove")
    
    stop_event = threading.Event()
    
    worker_thread = threading.Thread(target=run_worker, args=(stop_event,), daemon=True)
    worker_thread.start()
    file_bytes = b"brand new pdf content"
    response = client.post(
        "/upload", 
        files={"file": ("test.pdf", file_bytes)}, 
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    
    max_retries = 10
    final_status = None
    for _ in range(max_retries):
        status_response = client.get(
            f"/upload/status/{job_id}",
            headers={"X-API-Key": "test-api-key"}
        )
        if status_response.status_code == 200:
            final_status = status_response.json()["status"]
            if final_status in [JobStatus.completed, JobStatus.failed]:
                break
        time.sleep(0.5)
        
    assert final_status == JobStatus.completed
    assert response.json()["message"] == "Document accepted for processing"

    # Gracefully stop the worker thread
    stop_event.set()
    worker_thread.join(timeout=2.0)
