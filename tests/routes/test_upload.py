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

def test_upload_pdf_already_in_memory(client):
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
    assert data["message"] == "Document already processed and active"
    assert data["page_count"] == 5
    assert data["chunks"] == 10

def test_upload_pdf_in_redis_but_not_memory(client, mocker):
    file_bytes = b"hello pdf"
    
    # Mock cache hit for existing metadata
    mocker.patch("app.routes.upload.get_redis_metadata", return_value={
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
    assert data["message"] == "Document already processed and re-activated"
    assert data["page_count"] == 3
    assert data["chunks"] == 6

def test_upload_pdf_success_new_document(client, mocker):
    mocker.patch("app.routes.upload.get_redis_metadata", return_value=None)
    mocker.patch("app.routes.upload.extract_text_from_pdf", return_value=("Doc text", 1))
    mocker.patch("app.routes.upload.chunk_text", return_value=[{"index": 0, "text": "Doc text"}])
    mock_store_chunks = mocker.patch("app.routes.upload.store_document_chunks")
    mock_save_meta = mocker.patch("app.routes.upload.save_mongo_metadata")
    
    file_bytes = b"brand new pdf"
    
    response = client.post(
        "/upload", 
        files={"file": ("test.pdf", file_bytes)}, 
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Document uploaded and processed successfully"
    assert data["page_count"] == 1
    assert data["chunks"] == 1
    
    mock_store_chunks.assert_called_once()
    mock_save_meta.assert_called_once()
    
    # Verify memory is updated
    assert upload.DOCUMENT_STORE["file_name"] == "test.pdf"
    assert upload.DOCUMENT_STORE["chunk_count"] == 1

def test_upload_pdf_fails_in_storage(client, mocker):
    mocker.patch("app.routes.upload.get_redis_metadata", return_value=None)
    mocker.patch("app.routes.upload.extract_text_from_pdf", return_value=("Doc text", 1))
    mocker.patch("app.routes.upload.chunk_text", return_value=[])
    
    # Simulate DB upload failure
    mock_store_chunks = mocker.patch("app.routes.upload.store_document_chunks")
    mock_store_chunks.side_effect = Exception("Storage blew up")
    
    response = client.post(
        "/upload", 
        files={"file": ("test.pdf", b"pdf content")}, 
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 500
    assert "Failed to process document storage" in response.json()["detail"]
