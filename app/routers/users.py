from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.models.user import UserCreate, UserResponse, UserUpdate, ChangeStatusRequest, User, AddCreditsRequest, DeductCreditsRequest, ChangeUserTypeRequest, SearchUserRequest, UserLogin, ResetPasswordRequest
from app.database.user_service import (
    register_user_service, login_service, get_users_service,
    get_user_by_id_service, update_user_service, delete_user_service,
    change_user_status_service, add_credits_service, deduct_credits_service,
    change_user_type_service, search_users_service
)
from app.database.user_crud import reset_user_password

router = APIRouter(prefix="/users", tags=["users"])

# API Đăng ký tài khoản mới
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    API đăng ký tài khoản mới với username, email và password
    """
    return register_user_service(user, db)

# API Đăng nhập
@router.post("/login")
async def login_for_access_token(user_login: UserLogin, db: Session = Depends(get_db)):
    """
    API đăng nhập với username và password
    """
    return login_service(user_login.username, user_login.password, db)

# API Lấy danh sách tất cả tài khoản
@router.get("/", response_model=List[UserResponse])
async def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    API lấy danh sách tất cả người dùng trong hệ thống
    """
    return get_users_service(skip, limit, db)

# API Lấy thông tin tài khoản theo ID
@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int, 
    db: Session = Depends(get_db)
):
    """
    API lấy thông tin chi tiết của một người dùng theo ID
    """
    return get_user_by_id_service(user_id, db)

# API Cập nhật thông tin tài khoản theo ID
@router.put("/{user_id}", response_model=UserResponse)
async def update_user_info(
    user_id: int, 
    user_update: UserUpdate, 
    db: Session = Depends(get_db)
):
    """
    API cập nhật thông tin người dùng: tên đăng nhập, email, mật khẩu, số dư, loại tài khoản, trạng thái
    """
    # Gọi service không truyền current_user
    return update_user_service(user_id, user_update, None, db)

# API Xóa tài khoản
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    user_id: int, 
    db: Session = Depends(get_db)
):
    """
    API xóa tài khoản người dùng theo ID
    """
    # Gọi service không truyền current_user
    delete_user_service(user_id, None, db)
    return None

# API Thay đổi trạng thái tài khoản
@router.patch("/{user_id}/status", response_model=UserResponse)
async def change_account_status(
    user_id: int, 
    status_request: ChangeStatusRequest, 
    db: Session = Depends(get_db)
):
    """
    API thay đổi trạng thái hoạt động của tài khoản (kích hoạt/vô hiệu hóa)
    """
    # Gọi service không truyền current_user
    return change_user_status_service(user_id, status_request.active, None, db)

# API Nạp tiền vào tài khoản
@router.post("/{user_id}/add-credits", response_model=UserResponse)
async def add_credits(
    user_id: int,
    credits_request: AddCreditsRequest,
    db: Session = Depends(get_db)
):
    """
    API nạp tiền vào tài khoản người dùng
    """
    # Gọi service không truyền current_user
    return add_credits_service(user_id, credits_request.amount, None, db)

# API Trừ tiền từ tài khoản
@router.post("/{user_id}/deduct-credits", response_model=UserResponse)
async def deduct_credits(
    user_id: int,
    credits_request: DeductCreditsRequest,
    db: Session = Depends(get_db)
):
    """
    API trừ tiền từ tài khoản người dùng
    """
    # Gọi service không truyền current_user
    return deduct_credits_service(user_id, credits_request.amount, None, db)

# API Thay đổi loại tài khoản
@router.patch("/{user_id}/usertype", response_model=UserResponse)
async def change_user_type(
    user_id: int,
    usertype_request: ChangeUserTypeRequest,
    db: Session = Depends(get_db)
):
    """
    API thay đổi loại tài khoản (user/admin)
    """
    # Gọi service không truyền current_user
    return change_user_type_service(user_id, usertype_request.usertype, None, db)

# API Reset mật khẩu (chỉ admin)
@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    reset_data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    API reset mật khẩu người dùng - admin tự nhập mật khẩu mới
    Chỉ dành cho admin, không yêu cầu biết mật khẩu cũ
    """
    # Reset mật khẩu với mật khẩu được cung cấp
    updated_user = reset_user_password(db, user_id, reset_data.new_password)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản"
        )
    
    # Tạo response chứa thông tin cơ bản của user
    return {
        "id": updated_user.id,
        "username": updated_user.username,
        "email": updated_user.email,
        "usertype": updated_user.usertype,
        "active": updated_user.active,
        "credits": updated_user.credits,
        "message": "Đặt lại mật khẩu thành công"
    }

# API Tìm kiếm tài khoản
@router.post("/search", response_model=List[UserResponse])
async def search_users(
    search_request: SearchUserRequest,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    API tìm kiếm tài khoản theo từ khóa (username hoặc email)
    """
    return search_users_service(search_request.keyword, skip, limit, db) 