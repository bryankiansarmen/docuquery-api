import pytest
from fastapi import HTTPException
from app.dependencies import verify_api_key

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
