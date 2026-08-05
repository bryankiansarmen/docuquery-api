import sys
import importlib
import os
from unittest.mock import patch, MagicMock

# The real .env is loaded into os.environ when app.main is imported via conftest,
# so every test must explicitly control all mongo-related vars.
MONGO_VARS = [
    "MONGO_URL",
    "MONGO_HOST",
    "MONGO_PORT",
    "MONGO_SRV",
    "MONGO_USERNAME",
    "MONGO_PASSWORD",
]


def _mongo_env(**overrides):
    env = {
        "MONGO_URL": "",
        "MONGO_HOST": "",
        "MONGO_PORT": "27017",
        "MONGO_SRV": "false",
        "MONGO_USERNAME": "",
        "MONGO_PASSWORD": "",
    }
    env.update({k: str(v) for k, v in overrides.items()})
    return env


def test_mongo_connection_success():
    import app.db.mongo as mongo_module

    async_mock_cls = sys.modules['motor.motor_asyncio'].AsyncIOMotorClient
    sync_mock_cls = MagicMock()

    mock_async_client = MagicMock()
    mock_sync_client = MagicMock()
    async_mock_cls.return_value = mock_async_client
    sync_mock_cls.return_value = mock_sync_client

    with patch("app.db.mongo.MongoClient", sync_mock_cls):
        with patch.dict(os.environ, _mongo_env(MONGO_URL="mongodb://localhost")):
            importlib.reload(mongo_module)

            assert getattr(mongo_module, "mongo_client", None) is not None
            assert getattr(mongo_module, "mongo_client_sync", None) is not None


def test_mongo_connection_failure():
    import app.db.mongo as mongo_module

    async_mock_cls = sys.modules['motor.motor_asyncio'].AsyncIOMotorClient
    async_mock_cls.side_effect = Exception("Failed")

    with patch.dict(os.environ, _mongo_env(MONGO_URL="mongodb://localhost")):
        importlib.reload(mongo_module)

        assert getattr(mongo_module, "mongo_client", None) is None
        assert getattr(mongo_module, "mongo_client_sync", None) is None
    async_mock_cls.side_effect = None


def test_mongo_no_url():
    import app.db.mongo as mongo_module

    async_mock_cls = sys.modules['motor.motor_asyncio'].AsyncIOMotorClient
    async_mock_cls.reset_mock()

    with patch.dict(os.environ, _mongo_env()):
        importlib.reload(mongo_module)

        assert getattr(mongo_module, "mongo_client", None) is None
        async_mock_cls.assert_not_called()


def test_build_mongo_url_explicit_override():
    import app.db.mongo as mongo_module

    with patch.dict(os.environ, _mongo_env(MONGO_URL="mongodb://mongodb:27017", MONGO_USERNAME="u")):
        importlib.reload(mongo_module)
        assert mongo_module.build_mongo_url() == "mongodb://mongodb:27017"

    with patch.dict(os.environ, _mongo_env(MONGO_URL="", MONGO_USERNAME="u", MONGO_PASSWORD="p", MONGO_HOST="mongodb")):
        importlib.reload(mongo_module)
        assert mongo_module.build_mongo_url().startswith("mongodb://u:p@mongodb:27017")


def test_build_mongo_url_composes_from_credentials():
    import app.db.mongo as mongo_module

    env = _mongo_env(
        MONGO_URL="",
        MONGO_HOST="cluster0.example.mongodb.net",
        MONGO_USERNAME="docuquery",
        MONGO_PASSWORD="s3cret p@ss",
        MONGO_SRV="true",
    )
    with patch("app.db.mongo.MongoClient", MagicMock()):
        with patch.dict(os.environ, env):
            importlib.reload(mongo_module)
            url = mongo_module.build_mongo_url()

    assert url.startswith("mongodb+srv://docuquery:s3cret%20p%40ss@cluster0.example.mongodb.net/docuquery")
    assert "appName=DocuQuery" in url


def test_build_mongo_url_ignores_placeholder_url():
    import app.db.mongo as mongo_module

    env = _mongo_env(
        MONGO_URL="mongodb+srv://<db_username>:<db_password>@cluster0.example.mongodb.net/?appName=X",
        MONGO_HOST="cluster0.example.mongodb.net",
        MONGO_USERNAME="docuquery",
        MONGO_PASSWORD="s3cret",
        MONGO_SRV="true",
    )
    with patch("app.db.mongo.MongoClient", MagicMock()):
        with patch.dict(os.environ, env):
            importlib.reload(mongo_module)
            url = mongo_module.build_mongo_url()

    assert "docuquery:s3cret@" in url
    assert "Cluster0" not in url and "<db_username>" not in url
