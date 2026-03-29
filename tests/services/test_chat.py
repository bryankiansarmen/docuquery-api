import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.chat import get_chat_history, save_chat_turn

@pytest.mark.asyncio
async def test_get_chat_history(mock_mongo):
    mock_cursor_instance = MagicMock()
    mock_cursor_instance.to_list = AsyncMock()
    mock_cursor_instance.to_list.return_value = [
        {"question": "newest question", "answer": "a1"},
        {"question": "oldest question", "answer": "a2"}
    ]
    mock_mongo["chat"].find = MagicMock(return_value=mock_cursor_instance)

    history = await get_chat_history("document_id", "session_id")

    assert history == [
        {"question": "oldest question", "answer": "a2"},
        {"question": "newest question", "answer": "a1"}
    ]
    mock_mongo["chat"].find.assert_called_once_with(
        {"document_id": "document_id", "session_id": "session_id"},
        sort=[("timestamp", -1)],
        limit=10
    )

@pytest.mark.asyncio
async def test_save_chat_turn(mock_mongo):
    await save_chat_turn("doc1", "sess1", "q1", "a1")

    mock_mongo["chat"].insert_one.assert_called_once()
    args, kwargs = mock_mongo["chat"].insert_one.call_args
    document = args[0]
    
    assert document["document_id"] == "doc1"
    assert document["session_id"] == "sess1"
    assert document["question"] == "q1"
    assert document["answer"] == "a1"
    assert "timestamp" in document
