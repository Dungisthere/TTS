import sys
import os

# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.init_db import init_db

if __name__ == "__main__":
    print("Khởi tạo database...")
    # Tạo các bảng
    init_db()
    print("Đã khởi tạo database thành công!") 