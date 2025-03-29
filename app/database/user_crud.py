from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.models.user import User, UserCreate, UserUpdate
from typing import List, Optional

# Setup context cho việc băm mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hàm để băm mật khẩu
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Hàm để xác minh mật khẩu
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Lấy user theo username
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

# Lấy user theo email
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

# Lấy user theo id
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

# Lấy danh sách tất cả users
def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()

# Tạo user mới
def create_user(db: Session, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        password=hashed_password,
        email=user.email,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Cập nhật thông tin user
def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    user_data = user_update.dict(exclude_unset=True)
    
    # Nếu cập nhật mật khẩu, hãy băm nó
    if "password" in user_data and user_data["password"]:
        user_data["password"] = get_password_hash(user_data["password"])
    
    for key, value in user_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

# Thay đổi trạng thái user (active/inactive)
def change_user_status(db: Session, user_id: int, is_active: bool) -> Optional[User]:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    db_user.active = is_active
    db.commit()
    db.refresh(db_user)
    return db_user

# Xóa user
def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False
    
    db.delete(db_user)
    db.commit()
    return True 