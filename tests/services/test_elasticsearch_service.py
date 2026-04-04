from unittest.mock import MagicMock, patch
from app.services.elasticsearch import create_elasticsearch_index, index_chunks, hybrid_search, INDEX_NAME

@patch("app.services.elasticsearch.elasticsearch_client")
def test_create_elasticsearch_index_exists(mock_client):
    mock_client.indices.exists.return_value = True
    create_elasticsearch_index()
    mock_client.indices.create.assert_not_called()

@patch("app.services.elasticsearch.elasticsearch_client")
def test_create_elasticsearch_index_not_exists(mock_client):
    mock_client.indices.exists.return_value = False
    create_elasticsearch_index()
    mock_client.indices.create.assert_called_once()
    
def test_create_elasticsearch_index_no_client():
    with patch("app.services.elasticsearch.elasticsearch_client", None):
        create_elasticsearch_index() # Should return without error

@patch("app.services.elasticsearch.elasticsearch_client")
def test_index_chunks_success(mock_client):
    mock_llm_client = MagicMock()
    mock_llm_client.models.embed_content.return_value.embeddings = [MagicMock(values=[0.1, 0.2])]
    
    chunks = [{"index": 0, "text": "Hello world"}]
    index_chunks(chunks, "test.pdf", "doc_123", mock_llm_client)
    
    mock_client.index.assert_called_once()
    mock_client.indices.refresh.assert_called_once_with(index=INDEX_NAME)

@patch("app.services.elasticsearch.elasticsearch_client")
def test_index_chunks_embed_failure(mock_client):
    mock_llm_client = MagicMock()
    mock_llm_client.models.embed_content.side_effect = Exception("Embed fail")
    
    chunks = [{"index": 0, "text": "Hello world"}]
    index_chunks(chunks, "test.pdf", "doc_123", mock_llm_client)
    
    mock_client.index.assert_not_called()
    mock_client.indices.refresh.assert_called_once_with(index=INDEX_NAME)

def test_index_chunks_no_client():
    with patch("app.services.elasticsearch.elasticsearch_client", None):
        chunks = [{"index": 0, "text": "Hello world"}]
        index_chunks(chunks, "test.pdf", "doc_123", MagicMock()) # Should return without error

@patch("app.services.elasticsearch.elasticsearch_client")
def test_hybrid_search_success(mock_client):
    mock_llm_client = MagicMock()
    mock_llm_client.models.embed_content.return_value.embeddings = [MagicMock(values=[0.1, 0.2])]
    
    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {"_source": {"text": "result 1"}},
                {"_source": {"text": "result 2"}}
            ]
        }
    }
    
    results = hybrid_search("query", "doc_123", mock_llm_client)
    
    assert results == ["result 1", "result 2"]
    mock_client.search.assert_called_once()

@patch("app.services.elasticsearch.elasticsearch_client")
def test_hybrid_search_exception(mock_client):
    mock_llm_client = MagicMock()
    mock_client.search.side_effect = Exception("Search error")
    
    results = hybrid_search("query", "doc_123", mock_llm_client)
    assert results == []

def test_hybrid_search_no_client():
    with patch("app.services.elasticsearch.elasticsearch_client", None):
        results = hybrid_search("query", "doc_123", MagicMock())
        assert results == []
