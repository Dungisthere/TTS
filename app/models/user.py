from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from app.database.connection import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    credits = Column(BigInteger, default=0)
    usertype = Column(String(20), default="user")
    active = Column(Boolean, default=True)
    
    # Relationship với Voice Profiles
    voice_profiles = relationship("VoiceProfile", back_populates="user", cascade="all, delete")

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
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class ChangeStatusRequest(BaseModel):
    active: bool

class AddCreditsRequest(BaseModel):
    amount: int

class DeductCreditsRequest(BaseModel):
    amount: int

class ChangeUserTypeRequest(BaseModel):
    usertype: str

class ResetPasswordRequest(BaseModel):
    new_password: str

class SearchUserRequest(BaseModel):
    keyword: str 