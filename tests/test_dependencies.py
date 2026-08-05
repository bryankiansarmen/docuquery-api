import pytest
from fastapi import HTTPException
from app.dependencies import verify_api_key, get_tenant_id

def test_verify_api_key_valid():
    valid_key = "test-api-key"

    verify_api_key(valid_key)

    assert True

def test_verify_api_key_invalid():
    invalid_key = "wrong-key"

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(invalid_key)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Invalid API key"

@pytest.mark.asyncio
async def test_get_tenant_id_default():
    assert await get_tenant_id("default") == "default"

@pytest.mark.asyncio
async def test_get_tenant_id_from_header():
    assert await get_tenant_id("org-1") == "org-1"

@pytest.mark.asyncio
async def test_get_tenant_id_empty_falls_back_to_default():
    assert await get_tenant_id("") == "default"
