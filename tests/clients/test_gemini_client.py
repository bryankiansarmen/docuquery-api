import importlib
import os
from unittest.mock import patch, MagicMock

def test_gemini_connection_success():
    import app.clients.gemini as gemini_module
    
    mock_client_cls = MagicMock()
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    
    with patch("app.clients.gemini.genai.Client", mock_client_cls):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}):
            importlib.reload(gemini_module)
            
            assert getattr(gemini_module, "gemini_client", None) is not None
            mock_client_cls.assert_called_once_with(api_key="test")

def test_gemini_connection_failure():
    import app.clients.gemini as gemini_module
    
    mock_client_cls = MagicMock()
    mock_client_cls.side_effect = Exception("Failed")
    
    with patch("app.clients.gemini.genai.Client", mock_client_cls):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}):
            importlib.reload(gemini_module)
            
            assert getattr(gemini_module, "gemini_client", None) is None

def test_gemini_no_key():
    import app.clients.gemini as gemini_module
    
    mock_client_cls = MagicMock()
    
    with patch("app.clients.gemini.genai.Client", mock_client_cls):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            importlib.reload(gemini_module)
            
            assert getattr(gemini_module, "gemini_client", None) is None
            mock_client_cls.assert_not_called()
