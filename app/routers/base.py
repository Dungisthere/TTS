from fastapi import APIRouter
from fastapi import FastAPI, File, UploadFile, Header, HTTPException, Request, Form  # noqa: E402, F401

from app.security.security import get_api_key
from app.models.base import Base

# Tạo router cho người dùng
router = APIRouter(prefix="/base", tags=["base"])


@router.post("/base-url/", response_model=Base)
async def base_url(
    api_key: str = get_api_key,  # Khóa API để xác thực
    base_data: str = Form(""),
):
    #
    return base_data
