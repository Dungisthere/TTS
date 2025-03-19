from fastapi import Security  # noqa: E402
from fastapi import FastAPI, File, UploadFile, Header, HTTPException, Request, Form  # noqa: E402, F401
from fastapi.security import APIKeyHeader  # noqa: E402

from app.config import settings

# Định nghĩa header cho API key
api_key_header = APIKeyHeader(name="API-Key", auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == settings.API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate API Key")


get_api_key = Security(get_api_key)
