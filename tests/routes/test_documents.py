from unittest.mock import MagicMock, AsyncMock

def test_list_documents(client, mocker, mock_mongo):
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[
        {"document_id": "doc1", "file_name": "test1.pdf"}
    ])
    mock_mongo["document"].find.return_value = mock_cursor
    
    response = client.get("/documents", headers={"X-API-Key": "test-api-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert len(data["documents"]) == 1
    assert data["documents"][0]["document_id"] == "doc1"

def test_get_document_success(client, mocker, mock_mongo):
    mock_mongo["document"].find_one.return_value = {"document_id": "doc123", "file_name": "test.pdf"}
    
    response = client.get("/documents/doc123", headers={"X-API-Key": "test-api-key"})
    
    assert response.status_code == 200
    assert response.json()["document_id"] == "doc123"

def test_get_document_not_found(client, mocker, mock_mongo):
    mock_mongo["document"].find_one.return_value = None
    
    response = client.get("/documents/missing", headers={"X-API-Key": "test-api-key"})
    
    assert response.status_code == 404
    assert "Document not found" in response.json()["detail"]

    assert response.status_code == 404
    assert "Document not found" in response.json()["detail"]
