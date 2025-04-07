from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.models.user import UserCreate, UserUpdate, User
from app.database.user_crud import (
    create_user, get_users, get_user_by_id, update_user,
    delete_user, get_user_by_username, get_user_by_email,
    change_user_status, add_credits, deduct_credits, change_user_type,
    search_users
)
from app.database.auth import authenticate_user

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
def login_service(username: str, password: str, db: Session):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Trả về thông tin của user
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "credits": user.credits,
        "usertype": user.usertype,
        "active": user.active
    }

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
    # Loại bỏ các kiểm tra quyền, cho phép tất cả các thao tác
    
    updated_user = update_user(db, user_id, user_update)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản"
        )
    return updated_user

# Service xóa tài khoản
def delete_user_service(user_id: int, current_user: User, db: Session) -> Dict[str, str]:
    # Loại bỏ kiểm tra xóa tài khoản của chính mình
    
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
    # Loại bỏ kiểm tra vô hiệu hóa tài khoản của chính mình
    
    updated_user = change_user_status(db, user_id, is_active)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản"
        )
    return updated_user

# Service nạp tiền
def add_credits_service(
    user_id: int,
    amount: int,
    current_user: User,
    db: Session
) -> User:
    # Kiểm tra số tiền nạp
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số tiền nạp phải lớn hơn 0"
        )
    
    updated_user = add_credits(db, user_id, amount)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản"
        )
    return updated_user

# Service trừ tiền
def deduct_credits_service(
    user_id: int,
    amount: int,
    current_user: User,
    db: Session
) -> User:
    # Kiểm tra số tiền trừ
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số tiền trừ phải lớn hơn 0"
        )
    
    updated_user = deduct_credits(db, user_id, amount)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản hoặc số dư không đủ"
        )
    return updated_user

# Service thay đổi loại tài khoản
def change_user_type_service(
    user_id: int,
    usertype: str,
    current_user: User,
    db: Session
) -> User:
    # Kiểm tra loại tài khoản hợp lệ
    valid_user_types = ["user", "admin"]
    if usertype not in valid_user_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Loại tài khoản không hợp lệ. Chỉ chấp nhận: {', '.join(valid_user_types)}"
        )
    
    # Loại bỏ kiểm tra quyền hạn của current_user
    
    updated_user = change_user_type(db, user_id, usertype)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản"
        )
    return updated_user

# Service tìm kiếm user
def search_users_service(
    keyword: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = None
) -> List[User]:
    return search_users(db, keyword, skip=skip, limit=limit)

# Hàm helper để lấy user theo id hoặc trả về 404
def get_user_by_id_or_404(user_id: int, db: Session) -> User:
    """
    Lấy user theo ID, nếu không tìm thấy thì raise HTTP 404 exception
    """
    user = get_user_by_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người dùng với ID: {user_id}"
        )
    return user 