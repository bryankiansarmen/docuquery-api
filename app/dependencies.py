import os
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(key: str = Security(api_key_header)):
    if key != os.getenv("APP_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
