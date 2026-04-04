import sys
import importlib
from unittest.mock import MagicMock

def test_elasticsearch_connection_success():
    import app.db.elasticsearch as elasticsearch_module
    
    es_mock = sys.modules['elasticsearch'].Elasticsearch
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    es_mock.return_value = mock_client
    
    importlib.reload(elasticsearch_module)
    
    assert elasticsearch_module.elasticsearch_client is not None
    mock_client.ping.assert_called_once()

def test_elasticsearch_connection_ping_failure():
    import app.db.elasticsearch as elasticsearch_module
    
    es_mock = sys.modules['elasticsearch'].Elasticsearch
    mock_client = MagicMock()
    mock_client.ping.return_value = False
    es_mock.return_value = mock_client
    
    importlib.reload(elasticsearch_module)
    
    assert elasticsearch_module.elasticsearch_client is None
    mock_client.ping.assert_called_once()

def test_elasticsearch_connection_exception():
    import app.db.elasticsearch as elasticsearch_module
    
    es_mock = sys.modules['elasticsearch'].Elasticsearch
    es_mock.side_effect = Exception("Connection refused")
    
    importlib.reload(elasticsearch_module)
    
    assert elasticsearch_module.elasticsearch_client is None
    es_mock.side_effect = None  # Reset for other tests
