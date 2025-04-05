from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.models.config import ConfigUpdate, Config
from app.database.config_crud import get_config, upsert_config

# Service lấy cấu hình
def get_config_service(db: Session) -> Config:
    db_config = get_config(db)
    if db_config is None:
        # Nếu chưa có cấu hình, trả về lỗi hoặc tạo một cấu hình rỗng
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Chưa có cấu hình trong hệ thống"
        )
    return db_config

# Service cập nhật cấu hình
def update_config_service(config_update: ConfigUpdate, db: Session) -> Config:
    # Sử dụng hàm upsert để tạo mới hoặc cập nhật
    return upsert_config(db, config_update) 