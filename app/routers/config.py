from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.config import ConfigResponse, ConfigUpdate
from app.database.config_service import get_config_service, update_config_service

router = APIRouter(prefix="/config", tags=["config"])

# API Lấy cấu hình hiện tại
@router.get("/", response_model=ConfigResponse)
async def get_config(db: Session = Depends(get_db)):
    """
    API lấy thông tin cấu hình hệ thống
    """
    return get_config_service(db)

# API Cập nhật cấu hình
@router.put("/", response_model=ConfigResponse)
async def update_config(
    config_update: ConfigUpdate, 
    db: Session = Depends(get_db)
):
    """
    API cập nhật thông tin cấu hình hệ thống
    """
    return update_config_service(config_update, db) 