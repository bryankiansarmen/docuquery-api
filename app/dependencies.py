import os
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

APP_API_KEY = os.getenv("APP_API_KEY")
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

def verify_api_key(key: str = Security(API_KEY_HEADER)):
    if key != APP_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
