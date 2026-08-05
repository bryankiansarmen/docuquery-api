from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "tenant-1"}


def _seed_document_metadata(mock_mongo, file_name: str = "report.pdf"):
    metadata = {
        "document_id": "doc-1",
        "file_name": file_name,
        "uploaded_at": "2025-01-01T00:00:00Z",
        "chunk_count": 10,
        "page_count": 3,
        "user_id": "tenant-1",
    }
    mock_mongo["document"].find_one = AsyncMock(return_value=metadata)


def test_list_sessions_returns_grouped_sessions(mock_mongo):
    _seed_document_metadata(mock_mongo)

    grouped = [
        {
            "_id": "session-1",
            "title": "What is the summary?",
            "message_count": 4,
            "updated_at": "2025-01-02T00:00:00Z",
        }
    ]
    agg_cursor = AsyncMock()
    agg_cursor.to_list = AsyncMock(return_value=grouped)
    mock_mongo["chat"].aggregate.return_value = agg_cursor

    resp = client.get("/sessions", params={"document_id": "doc-1"}, headers=HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == "doc-1"
    assert body["sessions"][0]["session_id"] == "session-1"
    assert body["sessions"][0]["title"] == "What is the summary?"
    assert body["sessions"][0]["message_count"] == 4


def test_list_sessions_document_not_found(mock_mongo):
    mock_mongo["document"].find_one = AsyncMock(return_value=None)

    resp = client.get("/sessions", params={"document_id": "missing"}, headers=HEADERS)

    assert resp.status_code == 404


def test_session_messages_returns_turns(mock_mongo):
    _seed_document_metadata(mock_mongo)

    turns = [
        {
            "question": "Hello",
            "answer": "Hi there",
            "timestamp": "2025-01-02T00:00:00Z",
        },
        {
            "question": "Second",
            "answer": "Second answer",
            "timestamp": "2025-01-02T00:00:01Z",
        },
    ]
    mock_mongo["chat"].find.return_value.to_list = AsyncMock(return_value=turns)

    resp = client.get(
        "/sessions/session-1",
        params={"document_id": "doc-1"},
        headers=HEADERS,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "session-1"
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]
    assert body["messages"][0]["content"] == "Hello"


def test_session_messages_document_not_found(mock_mongo):
    mock_mongo["document"].find_one = AsyncMock(return_value=None)

    resp = client.get(
        "/sessions/session-1",
        params={"document_id": "missing"},
        headers=HEADERS,
    )

    assert resp.status_code == 404
