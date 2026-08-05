import json
from datetime import datetime, timezone
from app.services.cache import (
    create_answer_key, get_answer_cache, save_answer_cache,
    get_document_metadata, save_document_metadata, get_active_document
)

def test_create_answer_key():
    question = "What is this?"
    file_name = "test.pdf"

    key = create_answer_key(question, file_name)

    assert isinstance(key, str)
    assert len(key) == 64

def test_get_answer_cache_hit(mock_redis):
    mock_redis.get.return_value = json.dumps("cached answer")

    result = get_answer_cache("test_key")

    assert result == "cached answer"
    mock_redis.get.assert_called_once_with("test_key")

def test_get_answer_cache_miss(mock_redis):
    mock_redis.get.return_value = None

    result = get_answer_cache("test_key")

    assert result is None

def test_save_answer_cache(mock_redis):
    value = "new answer"

    save_answer_cache("test_key", value)

    mock_redis.setex.assert_called_once_with("test_key", 3600, json.dumps(value))

def test_document_metadata_operations(mock_redis):
    mock_redis.get.return_value = json.dumps({"document_id": "123", "page_count": 5})

    result = get_document_metadata("123")
    save_document_metadata("123", {"document_id": "123", "page_count": 5})

    assert result["page_count"] == 5
    assert mock_redis.set.call_count == 2

def test_document_metadata_operations_tenant_scoped(mock_redis):
    mock_redis.get.return_value = None

    get_document_metadata("123", tenant_id="org-1")
    save_document_metadata("123", {"document_id": "123"}, tenant_id="org-1")

    mock_redis.get.assert_called_once_with("document:org-1:123")
    set_keys = [call.args[0] for call in mock_redis.set.call_args_list]
    assert set_keys == ["document:org-1:123", "active_document:org-1"]

def test_save_document_metadata_handles_datetimes(mock_redis):
    meta = {
        "document_id": "123",
        "uploaded_at": datetime.now(timezone.utc),
    }
    # Must not raise on serialization of datetime values.
    save_document_metadata("123", meta, tenant_id="org-1")

    for call in mock_redis.set.call_args_list:
        stored = json.loads(call.args[1])
        assert stored["document_id"] == "123"
        assert "uploaded_at" in stored

def test_get_active_document_hit(mock_redis):
    mock_redis.get.return_value = json.dumps({"document_id": "active-123", "page_count": 10})

    result = get_active_document()

    assert result["document_id"] == "active-123"
    assert result["page_count"] == 10
    mock_redis.get.assert_called_once_with("active_document:default")

def test_get_active_document_miss(mock_redis):
    mock_redis.get.return_value = None

    result = get_active_document()

    assert result is None
    mock_redis.get.assert_called_once_with("active_document:default")