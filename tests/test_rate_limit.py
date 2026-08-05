import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException, Request


@pytest.fixture
def rate_limit_module():
    import app.rate_limit as rl
    return rl


@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.headers = {"X-API-Key": "test-api-key"}
    request.client = MagicMock(host="127.0.0.1")
    request.url.path = "/ask"
    return request


def test_identifier_prefers_api_key(rate_limit_module, mock_request):
    assert rate_limit_module._identifier(mock_request) == "test-api-key"


def test_identifier_falls_back_to_ip(rate_limit_module, mock_request):
    mock_request.headers = {}
    assert rate_limit_module._identifier(mock_request) == "127.0.0.1"


@pytest.mark.parametrize("current,limit,should_raise", [
    (1, 30, False),
    (30, 30, False),
    (31, 30, True),
])
@pytest.mark.asyncio
async def test_rate_limit_counts(rate_limit_module, mocker, mock_request, current, limit, should_raise):
    mock_redis_client = MagicMock()
    mock_redis_client.incr.return_value = current
    mock_redis_client.expire.return_value = True
    mocker.patch.object(rate_limit_module, "redis_client", mock_redis_client)
    mocker.patch.object(rate_limit_module, "RATE_LIMIT_ENABLED", True)

    dependency = rate_limit_module.rate_limit(limit, 60)

    if should_raise:
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_request)
        assert exc_info.value.status_code == 429
    else:
        await dependency(mock_request)

    mock_redis_client.incr.assert_called_once()
    if current == 1:
        mock_redis_client.expire.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limit_disabled(rate_limit_module, mocker, mock_request):
    mock_redis_client = MagicMock()
    mocker.patch.object(rate_limit_module, "redis_client", mock_redis_client)
    mocker.patch.object(rate_limit_module, "RATE_LIMIT_ENABLED", False)

    dependency = rate_limit_module.rate_limit(30, 60)
    await dependency(mock_request)

    mock_redis_client.incr.assert_not_called()


@pytest.mark.asyncio
async def test_rate_limit_fails_open_when_redis_down(rate_limit_module, mocker, mock_request):
    mocker.patch.object(rate_limit_module, "redis_client", None)
    mocker.patch.object(rate_limit_module, "RATE_LIMIT_ENABLED", True)

    dependency = rate_limit_module.rate_limit(30, 60)
    await dependency(mock_request)


@pytest.mark.asyncio
async def test_rate_limit_redis_error_does_not_raise(rate_limit_module, mocker, mock_request):
    mock_redis_client = MagicMock()
    mock_redis_client.incr.side_effect = Exception("Redis down")
    mocker.patch.object(rate_limit_module, "redis_client", mock_redis_client)
    mocker.patch.object(rate_limit_module, "RATE_LIMIT_ENABLED", True)

    dependency = rate_limit_module.rate_limit(30, 60)
    await dependency(mock_request)
