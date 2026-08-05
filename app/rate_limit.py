import os
from fastapi import Request, HTTPException, Depends
from loguru import logger
from app.db.redis import redis_client

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false"


def _identifier(request: Request) -> str:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    if request.client:
        return request.client.host
    return "anonymous"


def rate_limit(limit: int, window_seconds: int = 60):
    """Fixed-window rate limiter keyed by API key (falls back to client IP)."""
    async def dependency(request: Request):
        if not RATE_LIMIT_ENABLED:
            return
        if redis_client is None:
            logger.warning("Redis unavailable, skipping rate limit")
            return

        identifier = _identifier(request)
        redis_key = f"rate-limit:{request.url.path}:{identifier}"

        try:
            current = redis_client.incr(redis_key)
            if current == 1:
                redis_client.expire(redis_key, window_seconds)
            if current > limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Rate limit check failed for {identifier}: {e}")

    return dependency
