import sys
import importlib
import os
from unittest.mock import patch, MagicMock

def test_chroma_connection_success():
    import app.db.chroma as chroma_module
    
    chroma_mock = sys.modules['chromadb'].HttpClient
    mock_client = MagicMock()
    chroma_mock.return_value = mock_client
    
    with patch.dict(os.environ, {"CHROMA_HOST": "localhost"}):
        importlib.reload(chroma_module)
        
        assert getattr(chroma_module, "chroma_client", None) is not None
        assert mock_client.get_or_create_collection.call_count == 2
        mock_client.get_or_create_collection.assert_any_call("documents")
        mock_client.get_or_create_collection.assert_any_call("semantic_cache")

def test_chroma_connection_failure():
    import app.db.chroma as chroma_module
    
    chroma_mock = sys.modules['chromadb'].HttpClient
    chroma_mock.side_effect = Exception("Failed")
    
    with patch.dict(os.environ, {"CHROMA_HOST": "localhost"}):
        importlib.reload(chroma_module)
        
        assert getattr(chroma_module, "chroma_client", None) is None
    chroma_mock.side_effect = None

def test_chroma_no_host():
    import app.db.chroma as chroma_module
    
    chroma_mock = sys.modules['chromadb'].HttpClient
    chroma_mock.reset_mock()
    
    with patch.dict(os.environ, {"CHROMA_HOST": ""}):
        importlib.reload(chroma_module)
        
        assert getattr(chroma_module, "chroma_client", None) is None
        chroma_mock.assert_not_called()
