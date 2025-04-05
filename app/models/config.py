from sqlalchemy import Column, Integer, String, Text
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.database.connection import Base

class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    website_url = Column(String(255), nullable=True)
    website_name = Column(String(255), nullable=True)
    logo_base64 = Column(Text, nullable=True)
    phone_1 = Column(String(20), nullable=True)
    phone_2 = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)

# Pydantic models for API
class ConfigBase(BaseModel):
    website_url: Optional[str] = None
    website_name: Optional[str] = None
    logo_base64: Optional[str] = None
    phone_1: Optional[str] = None
    phone_2: Optional[str] = None
    email: Optional[str] = None

class ConfigCreate(ConfigBase):
    pass

class ConfigUpdate(ConfigBase):
    pass

class ConfigResponse(ConfigBase):
    id: int

    class Config:
        orm_mode = True 