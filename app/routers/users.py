from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.models.user import UserCreate, UserResponse, UserUpdate, ChangeStatusRequest, User
from app.database.auth import get_current_active_user, get_current_admin_user, Token
from app.database.user_service import (
    register_user_service, login_service, get_users_service,
    get_user_by_id_service, update_user_service, delete_user_service,
    change_user_status_service
)

router = APIRouter(prefix="/users", tags=["users"])

# Đăng ký tài khoản mới
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    return register_user_service(user, db)

# Đăng nhập
@router.post("/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return login_service(form_data.username, form_data.password, db)

# Lấy thông tin tài khoản hiện tại
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# Lấy danh sách tất cả tài khoản (chỉ admin)
@router.get("/", response_model=List[UserResponse])
async def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return get_users_service(skip, limit, db)

# Lấy thông tin tài khoản theo ID (chỉ admin)
@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return get_user_by_id_service(user_id, db)

# Cập nhật thông tin tài khoản theo ID (admin hoặc chủ tài khoản)
@router.put("/{user_id}", response_model=UserResponse)
async def update_user_info(
    user_id: int, 
    user_update: UserUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return update_user_service(user_id, user_update, current_user, db)

# Xóa tài khoản (chỉ admin)
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    delete_user_service(user_id, current_user, db)
    return None

# Thay đổi trạng thái tài khoản (chỉ admin)
@router.patch("/{user_id}/status", response_model=UserResponse)
async def change_account_status(
    user_id: int, 
    status_request: ChangeStatusRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return change_user_status_service(user_id, status_request.active, current_user, db) 