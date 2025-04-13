from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.models.user import User, UserCreate, UserUpdate
from typing import List, Optional
import random
import string

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

# Nạp tiền cho user
def add_credits(db: Session, user_id: int, amount: int) -> Optional[User]:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    db_user.credits += amount
    db.commit()
    db.refresh(db_user)
    return db_user

# Trừ tiền của user
def deduct_credits(db: Session, user_id: int, amount: int) -> Optional[User]:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    if db_user.credits < amount:
        return None  # Không đủ số dư
    
    db_user.credits -= amount
    db.commit()
    db.refresh(db_user)
    return db_user

# Thay đổi loại tài khoản
def change_user_type(db: Session, user_id: int, usertype: str) -> Optional[User]:
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    db_user.usertype = usertype
    db.commit()
    db.refresh(db_user)
    return db_user

# Tìm kiếm user
def search_users(db: Session, keyword: str, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).filter(
        (User.username.ilike(f"%{keyword}%")) | 
        (User.email.ilike(f"%{keyword}%"))
    ).offset(skip).limit(limit).all()

# Reset mật khẩu người dùng với mật khẩu được cung cấp
def reset_user_password(db: Session, user_id: int, new_password: str = None):
    # Tìm user
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    # Nếu không có mật khẩu mới được cung cấp, tạo mật khẩu ngẫu nhiên an toàn
    if new_password is None:
        # Độ dài 12 ký tự, gồm chữ hoa, chữ thường, số, ký tự đặc biệt
        characters = string.ascii_lowercase + string.ascii_uppercase + string.digits + "!@#$%^&*"
        password_length = 12
        
        # Đảm bảo mật khẩu có ít nhất 1 ký tự mỗi loại
        new_password = random.choice(string.ascii_lowercase)  # ít nhất 1 chữ thường
        new_password += random.choice(string.ascii_uppercase)  # ít nhất 1 chữ hoa
        new_password += random.choice(string.digits)  # ít nhất 1 số
        new_password += random.choice("!@#$%^&*")  # ít nhất 1 ký tự đặc biệt
        
        # Thêm các ký tự ngẫu nhiên cho đủ độ dài
        while len(new_password) < password_length:
            new_password += random.choice(characters)
        
        # Xáo trộn các ký tự để tăng tính ngẫu nhiên
        new_password_list = list(new_password)
        random.shuffle(new_password_list)
        new_password = ''.join(new_password_list)
        
        # Cập nhật mật khẩu đã băm vào database
        db_user.password = get_password_hash(new_password)
        db.commit()
        db.refresh(db_user)
        
        # Trả về cả user đã cập nhật và mật khẩu mới (chưa băm)
        return db_user, new_password
    
    # Nếu có mật khẩu mới được cung cấp
    db_user.password = get_password_hash(new_password)
    db.commit()
    db.refresh(db_user)
    
    # Trả về user đã cập nhật
    return db_user 