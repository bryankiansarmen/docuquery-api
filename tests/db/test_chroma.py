import sys
import importlib
import os
from unittest.mock import patch, MagicMock

def _reload_with_env(module_name: str, env: dict):
    module = importlib.import_module(module_name)
    with patch.dict(os.environ, env):
        importlib.reload(module)
    return module

def test_chroma_cloud_connection_success():
    import app.db.chroma as chroma_module

    env = {
        "CHROMA_API_KEY": "test-key",
        "CHROMA_TENANT": "test-tenant",
        "CHROMA_DATABASE": "docuquery",
        "CHROMA_HOST": "api.trychroma.com",
        "CHROMA_PORT": "443",
    }

    with patch.dict(os.environ, env):
        sys.modules['chromadb'].CloudClient.reset_mock()
        importlib.reload(chroma_module)

        assert chroma_module.chroma_client is not None
        assert chroma_module.chroma_client.get_or_create_collection.call_count == 2
        schema = chroma_module.build_schema()
        chroma_module.chroma_client.get_or_create_collection.assert_any_call(
            name="documents_default", schema=schema
        )
        chroma_module.chroma_client.get_or_create_collection.assert_any_call(
            name="semantic_cache_default", schema=schema
        )

def test_chroma_cloud_connection_failure():
    import app.db.chroma as chroma_module

    cloud_mock = sys.modules['chromadb'].CloudClient
    cloud_mock.side_effect = Exception("Failed")

    with patch.dict(os.environ, {"CHROMA_API_KEY": "test-key"}):
        importlib.reload(chroma_module)
        assert chroma_module.chroma_client is None

    cloud_mock.side_effect = None

def test_chroma_cloud_no_api_key():
    import app.db.chroma as chroma_module

    cloud_mock = sys.modules['chromadb'].CloudClient
    cloud_mock.reset_mock()

    with patch.dict(os.environ, {"CHROMA_API_KEY": ""}):
        importlib.reload(chroma_module)
        assert chroma_module.chroma_client is None
        cloud_mock.assert_not_called()

def test_collection_name_shards_by_tenant():
    import app.db.chroma as chroma_module

    assert chroma_module.collection_name("documents", None) == "documents_default"
    assert chroma_module.collection_name("documents", "org-1") == "documents_org-1"
    assert chroma_module.collection_name("semantic_cache", "org-1") == "semantic_cache_org-1"

def test_resolve_chroma_schemas_dir(tmp_path):
    import app.db.chroma as chroma_module

    bundled = tmp_path / "bundled"
    bundled.mkdir()

    # Falls back to the bundled schemas when the wheel schema dir is absent.
    missing = str(tmp_path / "missing")
    assert chroma_module.resolve_chroma_schemas_dir(missing, bundled) == str(bundled)

    # Prefers the wheel schema dir (no bundled copy shipped) when both absent returns real.
    assert chroma_module.resolve_chroma_schemas_dir(missing, tmp_path / "nope") == missing

    # Prefers the real (wheel) schema dir when it exists.
    real = tmp_path / "real"
    real.mkdir()
    assert chroma_module.resolve_chroma_schemas_dir(str(real), bundled) == str(real)
