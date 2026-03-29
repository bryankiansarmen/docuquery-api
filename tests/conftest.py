import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

import os
import sys

os.environ["APP_API_KEY"] = "test-api-key"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"

sys.modules['redis'] = MagicMock()
sys.modules['chromadb'] = MagicMock()
sys.modules['motor'] = MagicMock()
sys.modules['motor.motor_asyncio'] = MagicMock()

from app.main import app
from app.clients import gemini as gemini_mod

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True, scope="function")
def mock_redis(mocker):
    mock_redis_client = MagicMock()

    mocker.patch("app.services.cache.redis_client", mock_redis_client)

    return mock_redis_client

@pytest.fixture(autouse=True, scope="function")
def mock_chroma(mocker):
    mock_chroma_client = MagicMock()
    mock_doc_comp = MagicMock()
    mock_sem_comp = MagicMock()
    
    mocker.patch("app.services.vector.document_collection", mock_doc_comp)
    mocker.patch("app.services.vector.semantic_cache_collection", mock_sem_comp)
    
    return {
        "client": mock_chroma_client,
        "docs": mock_doc_comp,
        "semantic": mock_sem_comp
    }

@pytest.fixture(autouse=True, scope="function")
def mock_mongo(mocker):
    mock_chat_collection = MagicMock()
    mock_doc_collection = MagicMock()
    
    # Mock async methods specifically
    mock_chat_collection.insert_one = AsyncMock()
    mock_chat_collection.find_one = AsyncMock()
    mock_chat_collection.delete_one = AsyncMock()
    
    mock_doc_collection.update_one = AsyncMock()
    mock_doc_collection.find_one = AsyncMock()
    mock_doc_collection.delete_one = AsyncMock()
    
    mocker.patch("app.services.chat.chat_history_collection", mock_chat_collection)
    mocker.patch("app.services.document.document_metadata_collection", mock_doc_collection)

    return {
        "chat": mock_chat_collection,
        "document": mock_doc_collection
    }

@pytest.fixture(autouse=True, scope="function")
def mock_gemini(mocker):
    mock_client = MagicMock()
    
    # Mock embedding and generation defaults
    mock_response = MagicMock()
    mock_response.text = "Mocked answer"
    mock_client.models.generate_content.return_value = mock_response
    
    mock_embed_result = MagicMock()
    mock_embed_result.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    mock_client.models.embed_content.return_value = mock_embed_result

    mocker.patch.object(gemini_mod, "gemini_client", mock_client)
    
    return mock_client
