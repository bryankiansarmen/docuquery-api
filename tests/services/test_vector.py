from unittest.mock import MagicMock
from app.services.vector import (
    store_document_chunks, search_document_chunks,
    get_semantic_question_cache, save_semantic_question_cache
)

def test_store_document_chunks(mock_chroma):
    chunks = [
        {"index": 0, "text": "test chunk 1"},
        {"index": 1, "text": "test chunk 2"}
    ]

    store_document_chunks(chunks, "test.pdf", document_id="doc-hash")

    mock_chroma["docs"].add.assert_called_once()
    _, kwargs = mock_chroma["docs"].add.call_args
    assert kwargs["ids"] == ["doc-hash-0", "doc-hash-1"]
    assert kwargs["documents"] == ["test chunk 1", "test chunk 2"]
    assert kwargs["metadatas"][0]["document_id"] == "doc-hash"
    assert kwargs["metadatas"][0]["chunk_index"] == 0
    assert kwargs["metadatas"][0]["source"] == "test.pdf"

def test_store_document_chunks_uses_file_name_as_id(mock_chroma):
    chunks = [{"index": 0, "text": "test chunk 1"}]

    store_document_chunks(chunks, "test.pdf")

    _, kwargs = mock_chroma["docs"].add.call_args
    assert kwargs["ids"] == ["test.pdf-0"]

def test_store_document_chunks_no_client(mocker):
    mocker.patch("app.services.vector.document_collection", None)

    chunks = [{"index": 0, "text": "test chunk 1"}]
    store_document_chunks(chunks, "test.pdf")  # Should return without error

def test_store_document_chunks_tenant_shard(mocker):
    mock_tenant_col = MagicMock()
    mocker.patch("app.services.vector.get_document_collection", return_value=mock_tenant_col)

    store_document_chunks([{"index": 0, "text": "chunk"}], "test.pdf", "doc", "org-1")

    mock_tenant_col.add.assert_called_once()
    _, kwargs = mock_tenant_col.add.call_args
    assert kwargs["ids"] == ["doc-0"]

def test_search_document_chunks(mock_chroma):
    question = "What is the answer?"
    mock_chroma["docs"].search.return_value.rows.return_value = [
        [
            {"document": "Result 1", "score": 0.1},
            {"document": "Result 2", "score": 0.2}
        ]
    ]

    results = search_document_chunks(question)

    assert results == ["Result 1", "Result 2"]
    mock_chroma["docs"].search.assert_called_once()

def test_search_document_chunks_empty(mock_chroma):
    question = "What is the answer?"
    mock_chroma["docs"].search.return_value.rows.return_value = [[]]

    results = search_document_chunks(question)

    assert results == []

def test_search_document_chunks_filters_by_document(mock_chroma):
    mock_chroma["docs"].search.return_value.rows.return_value = [[]]

    results = search_document_chunks("question", document_id="doc-hash")

    assert results == []
    mock_chroma["docs"].search.assert_called_once()

def test_search_document_chunks_tenant_shard(mocker):
    mock_tenant_col = MagicMock()
    mock_tenant_col.search.return_value.rows.return_value = [
        [{"document": "Tenant result", "score": 0.1}]
    ]
    mocker.patch("app.services.vector.get_document_collection", return_value=mock_tenant_col)

    results = search_document_chunks("question", tenant_id="org-1")

    assert results == ["Tenant result"]
    mock_tenant_col.search.assert_called_once()

def test_search_document_chunks_no_client(mocker):
    mocker.patch("app.services.vector.document_collection", None)

    results = search_document_chunks("question")

    assert results == []

def test_get_semantic_question_cache_hit(mock_chroma):
    mock_chroma["semantic"].search.return_value.rows.return_value = [
        [{"document": "semantic answer", "score": 0.1, "metadata": {"source": "test.pdf"}}]
    ]

    response = get_semantic_question_cache("question", "test.pdf")

    assert response is not None
    assert response["answer"] == "semantic answer"
    assert response["metadata"]["source"] == "test.pdf"

def test_get_semantic_question_cache_miss_distance(mock_chroma):
    mock_chroma["semantic"].search.return_value.rows.return_value = [
        [{"document": "semantic answer", "score": 0.5, "metadata": {"source": "test.pdf"}}]
    ]

    response = get_semantic_question_cache("question", "test.pdf")

    assert response is None

def test_get_semantic_question_cache_no_rows(mock_chroma):
    mock_chroma["semantic"].search.return_value.rows.return_value = [[]]

    assert get_semantic_question_cache("question", "test.pdf") is None

def test_get_semantic_question_cache_no_client(mocker):
    mocker.patch("app.services.vector.semantic_cache_collection", None)

    assert get_semantic_question_cache("question", "test.pdf") is None

def test_save_semantic_question_cache(mock_chroma):
    save_semantic_question_cache("q", "a", "file.pdf")

    mock_chroma["semantic"].upsert.assert_called_once()

def test_save_semantic_question_cache_no_client(mocker):
    mocker.patch("app.services.vector.semantic_cache_collection", None)

    save_semantic_question_cache("q", "a", "file.pdf")  # Should not raise
