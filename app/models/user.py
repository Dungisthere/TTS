from sqlalchemy import Column, Integer, String, Boolean
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    credits = Column(Integer, default=0)
    usertype = Column(String(20), default="user")
    active = Column(Boolean, default=True)

# Pydantic models for API
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    credits: Optional[int] = None
    usertype: Optional[str] = None
    active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    credits: int
    usertype: str
    active: bool

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    username: str
    password: str

class ChangeStatusRequest(BaseModel):
    active: bool 