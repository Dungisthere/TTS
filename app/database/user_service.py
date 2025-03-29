from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import timedelta

from app.models.user import UserCreate, UserUpdate, User
from app.database.user_crud import (
    create_user, get_users, get_user_by_id, update_user,
    delete_user, get_user_by_username, get_user_by_email,
    change_user_status
)
from app.database.auth import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

# Service đăng ký tài khoản
def register_user_service(user: UserCreate, db: Session):
    # Kiểm tra username đã tồn tại chưa
    db_user = get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên đăng nhập đã tồn tại"
        )
    
    # Kiểm tra email đã tồn tại chưa
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng"
        )
    
    # Tạo user mới
    return create_user(db=db, user=user)

# Service đăng nhập
def login_service(username: str, password: str, db: Session) -> bool:
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Không tạo token nữa, chỉ trả về True
    return True

# Service lấy danh sách user
def get_users_service(skip: int = 0, limit: int = 100, db: Session = None) -> List[User]:
    return get_users(db, skip=skip, limit=limit)

# Service lấy user theo ID
def get_user_by_id_service(user_id: int, db: Session) -> User:
    db_user = get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Không tìm thấy tài khoản"
        )
    return db_user

# Service cập nhật thông tin user
def update_user_service(
    user_id: int, 
    user_update: UserUpdate, 
    current_user: User,
    db: Session
) -> User:
    # Chỉ admin hoặc chủ tài khoản mới được cập nhật
    if current_user.usertype != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không đủ quyền để thực hiện thao tác này"
        )
    
    # Chỉ admin mới được cập nhật usertype
    if current_user.usertype != "admin" and user_update.usertype is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới được cập nhật loại tài khoản"
        )
    
    # Chỉ admin mới được cập nhật credits
    if current_user.usertype != "admin" and user_update.credits is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới được cập nhật số dư credits"
        )
    
    updated_user = update_user(db, user_id, user_update)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản"
        )
    return updated_user

# Service xóa tài khoản
def delete_user_service(user_id: int, current_user: User, db: Session) -> Dict[str, str]:
    # Không thể xóa tài khoản của chính mình
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa tài khoản của chính mình"
        )
    
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản"
        )
    return {"status": "success"}

# Service thay đổi trạng thái tài khoản
def change_user_status_service(
    user_id: int, 
    is_active: bool, 
    current_user: User,
    db: Session
) -> User:
    # Không thể vô hiệu hóa tài khoản của chính mình
    if current_user.id == user_id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể vô hiệu hóa tài khoản của chính mình"
        )
    
    updated_user = change_user_status(db, user_id, is_active)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản"
        )
    return updated_user 