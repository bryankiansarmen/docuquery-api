import json, os, hmac
from fastapi import Request, Security, HTTPException, Header
from fastapi.security import APIKeyHeader
from loguru import logger

APP_API_KEY = os.getenv("APP_API_KEY")
APP_API_KEYS = os.getenv("APP_API_KEYS")

# Optional per-tenant key mapping: {"tenant_id": "api_key", ...}. When set, the
# X-API-Key identifies the tenant and self-declared tenant headers are ignored,
# turning tenant sharding into an actual auth boundary.
_tenant_api_keys = {}
if APP_API_KEYS:
    try:
        _tenant_api_keys = json.loads(APP_API_KEYS)
    except Exception as e:
        logger.error(f"Invalid APP_API_KEYS JSON: {e}")

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _secure_equal(a, b) -> bool:
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    return hmac.compare_digest(a, b)


def _resolve_tenant(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if APP_API_KEY and _secure_equal(api_key, APP_API_KEY):
        return "default"
    for tenant, key in _tenant_api_keys.items():
        if _secure_equal(api_key, key):
            return tenant
    return None


def verify_api_key(key: str = Security(API_KEY_HEADER)):
    if not key:
        raise HTTPException(status_code=401, detail="Missing API key")
    if _resolve_tenant(key) is None:
        raise HTTPException(status_code=403, detail="Invalid API key")


async def get_tenant_id(
    request: Request,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> str:
    """Resolve the tenant/org used to shard data.

    When per-tenant keys (APP_API_KEYS) are configured the tenant is derived
    from the authenticated API key and the self-declared X-Tenant-Id header is
    ignored. Otherwise the X-Tenant-Id header is used (single shared key mode).

    Declaring ``X-Tenant-Id`` as a ``Header`` exposes it in the OpenAPI spec and
    the interactive Swagger UI, so tools like the docs no longer silently fall
    back to the ``default`` tenant and return empty results.
    """
    key = request.headers.get("X-API-Key") or ""
    if _tenant_api_keys:
        tenant = _resolve_tenant(key)
        if tenant is None:
            raise HTTPException(status_code=403, detail="Invalid API key")
        return tenant
    return x_tenant_id or "default"
