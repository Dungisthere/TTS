from sqlalchemy.orm import Session
from app.models.config import Config, ConfigCreate, ConfigUpdate
from typing import List, Optional

# Lấy cấu hình từ database (luôn chỉ có 1 bản ghi duy nhất)
def get_config(db: Session) -> Optional[Config]:
    return db.query(Config).first()

# Tạo hoặc cập nhật cấu hình (upsert)
def upsert_config(db: Session, config_data: ConfigUpdate) -> Config:
    # Kiểm tra xem đã có cấu hình chưa
    db_config = get_config(db)
    
    # Nếu chưa có, tạo mới
    if not db_config:
        db_config = Config()
        db.add(db_config)
    
    # Cập nhật các trường
    config_data_dict = config_data.dict(exclude_unset=True)
    for key, value in config_data_dict.items():
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    return db_config

# Lấy config theo id
def get_config_by_id(db: Session, config_id: int) -> Optional[Config]:
    return db.query(Config).filter(Config.id == config_id).first()

# Lấy tất cả config
def get_all_configs(db: Session, skip: int = 0, limit: int = 100) -> List[Config]:
    return db.query(Config).offset(skip).limit(limit).all()

# Tạo config mới
def create_config(db: Session, config: ConfigCreate) -> Config:
    db_config = Config(
        website_url=config.website_url,
        website_name=config.website_name,
        logo_base64=config.logo_base64,
        phone_1=config.phone_1,
        phone_2=config.phone_2,
        email=config.email
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

# Cập nhật thông tin config
def update_config(db: Session, config_id: int, config_update: ConfigUpdate) -> Optional[Config]:
    db_config = get_config_by_id(db, config_id)
    if not db_config:
        return None
    
    config_data = config_update.dict(exclude_unset=True)
    
    for key, value in config_data.items():
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    return db_config

# Xóa config
def delete_config(db: Session, config_id: int) -> bool:
    db_config = get_config_by_id(db, config_id)
    if not db_config:
        return False
    
    db.delete(db_config)
    db.commit()
    return True 