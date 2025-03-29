# API Quản Lý Tài Khoản Người Dùng

## Cài đặt

1. Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

2. Tạo database MySQL:
```sql
CREATE DATABASE db_tts;
```

3. Khởi tạo database:
```bash
python scripts/init_database.py
```

## Thông tin kết nối

- Database: MySQL
- Host: 127.0.0.1
- Database name: db_tts
- Thông tin kết nối được cấu hình trong `app/database/connection.py`

## Các API

### 1. Đăng ký tài khoản

- **URL**: `/users/register`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "username": "example_user",
    "email": "user@example.com",
    "password": "password123"
  }
  ```
- **Response**:
  ```json
  {
    "id": 2,
    "username": "example_user",
    "email": "user@example.com",
    "credits": 0,
    "usertype": "user",
    "active": true
  }
  ```

### 2. Đăng nhập

- **URL**: `/users/login`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "username": "example_user",
    "password": "password123"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```

### 3. Lấy thông tin tài khoản hiện tại

- **URL**: `/users/me`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer {token}`
- **Response**:
  ```json
  {
    "id": 2,
    "username": "example_user",
    "email": "user@example.com",
    "credits": 0,
    "usertype": "user",
    "active": true
  }
  ```

### 4. Lấy danh sách tài khoản (chỉ admin)

- **URL**: `/users/`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer {token}`
- **Query Parameters**: `skip=0&limit=100`
- **Response**:
  ```json
  [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "credits": 1000,
      "usertype": "admin",
      "active": true
    },
    {
      "id": 2,
      "username": "example_user",
      "email": "user@example.com",
      "credits": 0,
      "usertype": "user",
      "active": true
    }
  ]
  ```

### 5. Lấy thông tin tài khoản theo ID (chỉ admin)

- **URL**: `/users/{user_id}`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer {token}`
- **Response**:
  ```json
  {
    "id": 2,
    "username": "example_user",
    "email": "user@example.com",
    "credits": 0,
    "usertype": "user",
    "active": true
  }
  ```

### 6. Cập nhật thông tin tài khoản

- **URL**: `/users/{user_id}`
- **Method**: `PUT`
- **Headers**: `Authorization: Bearer {token}`
- **Body**:
  ```json
  {
    "username": "new_username",
    "email": "new_email@example.com",
    "password": "new_password"
  }
  ```
- **Response**:
  ```json
  {
    "id": 2,
    "username": "new_username",
    "email": "new_email@example.com",
    "credits": 0,
    "usertype": "user",
    "active": true
  }
  ```

### 7. Xóa tài khoản (chỉ admin)

- **URL**: `/users/{user_id}`
- **Method**: `DELETE`
- **Headers**: `Authorization: Bearer {token}`
- **Response**: No content (204)

### 8. Thay đổi trạng thái tài khoản (chỉ admin)

- **URL**: `/users/{user_id}/status`
- **Method**: `PATCH`
- **Headers**: `Authorization: Bearer {token}`
- **Body**:
  ```json
  {
    "active": false
  }
  ```
- **Response**:
  ```json
  {
    "id": 2,
    "username": "example_user",
    "email": "user@example.com",
    "credits": 0,
    "usertype": "user",
    "active": false
  }
  ```

## Lưu ý

1. Mật khẩu được mã hóa trước khi lưu vào database
2. Chỉ admin mới có thể xem danh sách tài khoản, xóa tài khoản, thay đổi trạng thái
3. Người dùng thường chỉ có thể cập nhật thông tin tài khoản của mình 