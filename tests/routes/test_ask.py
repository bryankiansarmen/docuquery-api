import pytest
from app.routes import ask
from app.services import store as store_mod
from unittest.mock import AsyncMock

DEFAULT_METADATA = {
    "document_id": "test_id",
    "file_name": "test.pdf",
    "page_count": 2,
    "chunk_count": 3,
}


@pytest.fixture(autouse=True)
def mock_dependencies(mocker):
    mocker.patch.object(store_mod, "DOCUMENT_STORE", {})
    mocker.patch("app.routes.ask.get_chat_history", new_callable=AsyncMock, return_value=[])
    mocker.patch("app.routes.ask.save_chat_turn", new_callable=AsyncMock)
    mocker.patch("app.routes.ask.generate_answer", return_value="Here is the AI answer")
    mocker.patch("app.routes.ask.search_document_chunks", return_value=["Some chunk context"])
    # An explicit document_id resolves from Mongo unless a test overrides this.
    mocker.patch("app.routes.ask.get_document_metadata", new_callable=AsyncMock, return_value=DEFAULT_METADATA)


def test_ask_no_document(client, mocker):
    # Blank global state; explicit doc id that cannot be resolved must 400.
    mocker.patch.object(store_mod, "DOCUMENT_STORE", {})
    mocker.patch("app.routes.ask.get_document_metadata", new_callable=AsyncMock, return_value=None)
    mocker.patch("app.routes.ask.get_active_document", return_value=None)

    request_body = {"message": "Query", "document_id": "doc_123"}

    response = client.post("/ask", json=request_body, headers={"X-API-Key": "test-api-key"})

    assert response.status_code == 400
    assert "Document not found" in response.json()["detail"]


def test_ask_recovers_active_document_from_redis(client, mocker):
    mocker.patch.object(store_mod, "DOCUMENT_STORE", {})
    mocker.patch("app.routes.ask.get_active_document",
                 return_value={"file_name": "redis_recover.pdf", "document_id": "recover_id"})
    mocker.patch("app.routes.ask.get_answer_cache", return_value=None)
    mocker.patch("app.routes.ask.get_semantic_question_cache", return_value=None)

    # No explicit document_id -> fall back to the active document in Redis.
    request_body = {"message": "Query", "document_id": ""}

    response = client.post("/ask", json=request_body, headers={"X-API-Key": "test-api-key"})

    assert response.status_code == 200
    assert response.json()["source_file"] == "redis_recover.pdf"
    assert store_mod.DOCUMENT_STORE["default"]["file_name"] == "redis_recover.pdf"


def test_ask_exact_cache_hit(client, mocker):
    mocker.patch("app.routes.ask.get_answer_cache", return_value="cached exact answer")

    request_body = {"message": "Query", "document_id": "test_id"}

    response = client.post("/ask", json=request_body, headers={"X-API-Key": "test-api-key"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "cached exact answer"
    assert data["cache_type"] == "exact"
    assert data["source_file"] == "test.pdf"
    assert "session_id" in data
    # Cache hits still persist the turn so multi-turn history is consistent.
    ask.save_chat_turn.assert_awaited_once()


def test_ask_semantic_cache_hit(client, mocker):
    mocker.patch("app.routes.ask.get_answer_cache", return_value=None)
    mocker.patch("app.routes.ask.get_semantic_question_cache", return_value={
        "answer": "semantic answer",
        "metadata": {"source": "test.pdf"}
    })

    request_body = {"message": "Query", "document_id": "test_id"}

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
    assert "Internal server error" in response.json()["detail"]