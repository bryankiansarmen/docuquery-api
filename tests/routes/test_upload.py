import pytest
from app.routes import upload
import hashlib

@pytest.fixture(autouse=True)
def clean_document_store():
    # Reset internal memory state before each test
    upload.DOCUMENT_STORE.clear()

def test_upload_non_pdf(client):
    response = client.post(
        "/upload", 
        files={"file": ("test.txt", b"hello text")}, 
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]

def test_upload_pdf_already_active_in_memory(client):
    file_bytes = b"hello pdf"
    document_id = hashlib.sha256(file_bytes).hexdigest()
    
    upload.DOCUMENT_STORE.update({
        "document_id": document_id,
        "page_count": 5,
        "chunk_count": 10
    })
    
    response = client.post(
        "/upload", 
        files={"file": ("test.pdf", file_bytes)}, 
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Document already active"
    assert data["status"] == "completed"

def test_upload_pdf_already_in_redis(client, mocker):
    file_bytes = b"hello pdf"
    document_id = hashlib.sha256(file_bytes).hexdigest()
    
    # Mock cache hit for existing metadata
    mocker.patch("app.routes.upload.get_redis_metadata", return_value={
        "document_id": document_id,
        "file_name": "test.pdf",
        "page_count": 3,
        "chunk_count": 6
    })
    
    response = client.post(
        "/upload", 
        files={"file": ("test.pdf", file_bytes)}, 
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Document already processed"
    assert data["status"] == "completed"
    
    # Verify memory store was updated from cache
    assert upload.DOCUMENT_STORE["document_id"] == document_id

def test_upload_pdf_success_async_start(client, mocker):
    mocker.patch("app.routes.upload.get_redis_metadata", return_value=None)
    mock_publish = mocker.patch("app.routes.upload.publish_upload_job", return_value="test-job-id")
    
    file_bytes = b"brand new pdf"
    
    response = client.post(
        "/upload", 
        files={"file": ("test.pdf", file_bytes)}, 
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Document accepted for processing"
    assert data["job_id"] == "test-job-id"
    assert data["status"] == "pending"
    
    mock_publish.assert_called_once()

def test_get_upload_status_success(client, mocker):
    mocker.patch("app.routes.upload.get_job_status", return_value={
        "job_id": "test-job",
        "status": "processing",
        "message": "Working on it"
    })
    
    response = client.get(
        "/upload/status/test-job",
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "processing"

def test_get_upload_status_not_found(client, mocker):
    mocker.patch("app.routes.upload.get_job_status", return_value=None)
    
    response = client.get(
        "/upload/status/missing-job",
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]
