import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.dependencies import verify_api_key, get_tenant_id


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
    assert await get_tenant_id(_make_request()) == "default"


@pytest.mark.asyncio
async def test_get_tenant_id_from_header():
    assert await get_tenant_id(_make_request({"X-Tenant-Id": "org-1"})) == "org-1"


@pytest.mark.asyncio
async def test_get_tenant_id_empty_falls_back_to_default():
    assert await get_tenant_id(_make_request({"X-Tenant-Id": ""})) == "default"