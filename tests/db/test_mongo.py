import sys
import importlib
import os
from unittest.mock import patch, MagicMock

def test_mongo_connection_success():
    import app.db.mongo as mongo_module
    
    async_mock_cls = sys.modules['motor.motor_asyncio'].AsyncIOMotorClient
    sync_mock_cls = MagicMock()
    
    mock_async_client = MagicMock()
    mock_sync_client = MagicMock()
    async_mock_cls.return_value = mock_async_client
    sync_mock_cls.return_value = mock_sync_client
    
    with patch("app.db.mongo.MongoClient", sync_mock_cls):
        with patch.dict(os.environ, {"MONGO_URL": "mongodb://localhost"}):
            importlib.reload(mongo_module)
            
            assert getattr(mongo_module, "mongo_client", None) is not None
            assert getattr(mongo_module, "mongo_client_sync", None) is not None

def test_mongo_connection_failure():
    import app.db.mongo as mongo_module
    
    async_mock_cls = sys.modules['motor.motor_asyncio'].AsyncIOMotorClient
    async_mock_cls.side_effect = Exception("Failed")
    
    with patch.dict(os.environ, {"MONGO_URL": "mongodb://localhost"}):
        importlib.reload(mongo_module)
        
        assert getattr(mongo_module, "mongo_client", None) is None
        assert getattr(mongo_module, "mongo_client_sync", None) is None
    async_mock_cls.side_effect = None

def test_mongo_no_url():
    import app.db.mongo as mongo_module
    
    async_mock_cls = sys.modules['motor.motor_asyncio'].AsyncIOMotorClient
    async_mock_cls.reset_mock()
    
    with patch.dict(os.environ, {"MONGO_URL": ""}):
        importlib.reload(mongo_module)
        
        assert getattr(mongo_module, "mongo_client", None) is None
        async_mock_cls.assert_not_called()
