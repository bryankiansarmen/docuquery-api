import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.dependencies import verify_api_key, get_tenant_id
from app.main import app


def _make_request(headers=None):
    request = MagicMock()
    request.headers = {"X-API-Key": "test-api-key", **(headers or {})}
    return request


def test_verify_api_key_valid():
    verify_api_key("test-api-key")
    assert True


def test_verify_api_key_invalid():
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key("wrong-key")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Invalid API key"


def test_verify_api_key_missing():
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing API key"


@pytest.mark.asyncio
async def test_get_tenant_id_default():
    assert await get_tenant_id(_make_request(), None) == "default"


@pytest.mark.asyncio
async def test_get_tenant_id_from_header():
    assert await get_tenant_id(_make_request(), "org-1") == "org-1"


@pytest.mark.asyncio
async def test_get_tenant_id_empty_falls_back_to_default():
    assert await get_tenant_id(_make_request(), "") == "default"


def test_tenant_header_reaches_storage_scoping(mock_mongo):
    """X-Tenant-Id must flow from the request into the document query."""
    client = TestClient(app)

    mock_find = MagicMock()
    mock_find.sort.return_value = mock_find
    mock_find.to_list = AsyncMock(return_value=[])
    mock_mongo["document"].find.return_value = mock_find

    resp = client.get(
        "/documents",
        headers={"X-API-Key": "test-api-key", "X-Tenant-Id": "org-42"},
    )

    assert resp.status_code == 200
    call_args, _ = mock_mongo["document"].find.call_args
    assert call_args[0]["user_id"] == "org-42"


def test_tenant_header_visible_in_openapi_spec():
    """The tenant header must be declared so tools like Swagger can send it."""
    client = TestClient(app)
    spec = client.get("/openapi.json").json()

    tenant_header_paths = 0
    for operation in spec["paths"].values():
        for method in operation.values():
            params = method.get("parameters", [])
            if any(
                p.get("in") == "header" and p.get("name") == "X-Tenant-Id"
                for p in params
            ):
                tenant_header_paths += 1

    assert tenant_header_paths > 0