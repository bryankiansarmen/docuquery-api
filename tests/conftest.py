import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

import os
import sys

os.environ["APP_API_KEY"] = "test-api-key"
os.environ["OPENROUTER_API_KEY"] = "test-openrouter-key"
os.environ["OPENROUTER_CHAT_MODEL"] = "deepseek/deepseek-chat"
os.environ["OPENROUTER_EMBEDDING_MODEL"] = "baai/bge-m3"

sys.modules['redis'] = MagicMock()
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.utils'] = MagicMock()
sys.modules['chromadb.utils.embedding_functions'] = MagicMock()
sys.modules['chromadb.execution'] = MagicMock()
sys.modules['chromadb.execution.expression'] = MagicMock()
sys.modules['chromadb.execution.expression.operator'] = MagicMock()
sys.modules['motor'] = MagicMock()
sys.modules['motor.motor_asyncio'] = MagicMock()


from app.main import app
from app.clients import openrouter as openrouter_mod

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True, scope="function")
def mock_redis(mocker):
    mock_redis_client = MagicMock()
    mock_redis_client.get.return_value = None
    mock_redis_client.incr.return_value = 1
    mock_redis_client.expire.return_value = True

    mocker.patch("app.db.redis.redis_client", mock_redis_client)
    mocker.patch("app.rate_limit.redis_client", mock_redis_client)
    mocker.patch("app.services.cache.redis_client", mock_redis_client)
    mocker.patch("app.services.stream.redis_client", mock_redis_client)
    
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
    # Default find_one to None (docs lookups miss unless a test sets a value).
    mock_doc_collection.find_one = AsyncMock(return_value=None)
    mock_doc_collection.delete_one = AsyncMock()
    
    mocker.patch("app.services.chat.chat_history_collection", mock_chat_collection)
    mocker.patch("app.services.document.document_metadata_collection", mock_doc_collection)

    return {
        "chat": mock_chat_collection,
        "document": mock_doc_collection
    }

@pytest.fixture(autouse=True, scope="function")
def mock_openrouter(mocker):
    mock_client = MagicMock()

    # Mock chat completion defaults
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Mocked answer"
    mock_client.chat.completions.create.return_value = mock_completion

    # Mock embedding defaults
    mock_embed = MagicMock()
    mock_embed.data = [MagicMock(index=0, embedding=[0.1, 0.2, 0.3])]
    mock_client.embeddings.create.return_value = mock_embed

    mocker.patch.object(openrouter_mod, "openrouter_client", mock_client)
    mocker.patch.object(openrouter_mod, "_embedding_client", mock_client)

    return mock_client
