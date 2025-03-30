from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.database.connection import get_db
from app.database.user_crud import get_user_by_username, verify_password
from app.models.user import User

# Hàm xác thực người dùng
def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    if not user.active:
        return None
    return user 