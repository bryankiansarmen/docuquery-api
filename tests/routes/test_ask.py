import pytest
from app.routes import ask
from unittest.mock import AsyncMock

@pytest.fixture(autouse=True)
def mock_dependencies(mocker):
    mocker.patch.object(ask, "DOCUMENT_STORE", {"file_name": "test.pdf"})
    mocker.patch("app.routes.ask.get_chat_history", new_callable=AsyncMock, return_value=[])
    mocker.patch("app.routes.ask.save_chat_turn", new_callable=AsyncMock)
    mocker.patch("app.routes.ask.generate_answer", return_value="Here is the AI answer")
    mocker.patch("app.routes.ask.search_document_chunks", return_value=["Some chunk context"])
    mocker.patch("app.routes.ask.hybrid_search", return_value=["Some hybrid context"])

def test_ask_no_document(client, mocker):
    # Blank the global memory document state and ensure redis metadata also responds empty
    mocker.patch.object(ask, "DOCUMENT_STORE", {})
    mocker.patch("app.routes.ask.get_active_document", return_value=None)
    
    request_body = {"message": "Query", "document_id": "doc_123"}
    
    response = client.post("/ask", json=request_body, headers={"X-API-Key": "test-api-key"})
    
    assert response.status_code == 400
    assert "No document uploaded yet" in response.json()["detail"]

def test_ask_recovers_active_document_from_redis(client, mocker):
    mocker.patch.object(ask, "DOCUMENT_STORE", {})
    mocker.patch("app.routes.ask.get_active_document", return_value={"file_name": "redis_recover.pdf"})
    mocker.patch("app.routes.ask.get_answer_cache", return_value=None)
    mocker.patch("app.routes.ask.get_semantic_question_cache", return_value=None)
    mocker.patch("app.routes.ask.save_answer_cache")
    mocker.patch("app.routes.ask.save_semantic_question_cache")
    
    request_body = {"message": "Query", "document_id": "doc_123"}
    
    response = client.post("/ask", json=request_body, headers={"X-API-Key": "test-api-key"})
    
    assert response.status_code == 200
    assert response.json()["source_file"] == "redis_recover.pdf"
    assert ask.DOCUMENT_STORE["file_name"] == "redis_recover.pdf"

def test_ask_exact_cache_hit(client, mocker):
    mocker.patch("app.routes.ask.get_answer_cache", return_value={"answer": "cached exact answer"})
    
    request_body = {"message": "Query", "document_id": "doc_123"}
    
    response = client.post("/ask", json=request_body, headers={"X-API-Key": "test-api-key"})
    
    assert response.status_code == 200
    assert response.json()["answer"] == "cached exact answer"

def test_ask_semantic_cache_hit(client, mocker):
    mocker.patch("app.routes.ask.get_answer_cache", return_value=None)
    mocker.patch("app.routes.ask.get_semantic_question_cache", return_value={
        "answer": "semantic answer",
        "metadata": {"source": "test.pdf"}
    })
    
    request_body = {"message": "Query", "document_id": "doc_123"}
    
    response = client.post("/ask", json=request_body, headers={"X-API-Key": "test-api-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "semantic answer"
    assert data["cache_type"] == "semantic_question"

def test_ask_full_ai_generation(client, mocker):
    mocker.patch("app.routes.ask.get_answer_cache", return_value=None)
    mocker.patch("app.routes.ask.get_semantic_question_cache", return_value=None)
    
    mock_save_cache = mocker.patch("app.routes.ask.save_answer_cache")
    mock_save_semantic = mocker.patch("app.routes.ask.save_semantic_question_cache")
    
    request_body = {"message": "Query", "document_id": "test_id"}
    
    response = client.post("/ask", json=request_body, headers={"X-API-Key": "test-api-key"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Here is the AI answer"
    assert data["source_file"] == "test.pdf"
    assert "session_id" in data
    
    # Verification of persistence
    mock_save_cache.assert_called_once()
    mock_save_semantic.assert_called_once()
    
def test_ask_fails_server_error(client, mocker):
    mocker.patch("app.routes.ask.get_answer_cache", return_value=None)
    mocker.patch("app.routes.ask.get_semantic_question_cache", return_value=None)
    
    mock_gen = mocker.patch("app.routes.ask.generate_answer")
    mock_gen.side_effect = Exception("LLM is down!")
    
    request_body = {"message": "Query", "document_id": "test_id"}
    
    response = client.post("/ask", json=request_body, headers={"X-API-Key": "test-api-key"})
    
    assert response.status_code == 500
    assert "LLM is down!" in response.json()["detail"]
