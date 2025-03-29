from fastapi import FastAPI, Depends
from app.routers import base, file_upload, users, tts_facebook
from fastapi.middleware.cors import CORSMiddleware
from app.database.init_db import init_db
from app.database.connection import get_db
from sqlalchemy.orm import Session


# Tạo instance của FastAPI
app = FastAPI()

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả nguồn (hoặc chỉ định danh sách ["http://example.com"])
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả phương thức (GET, POST, PUT, DELETE, v.v.)
    allow_headers=["*"],  # Cho phép tất cả headers
)

# Khởi tạo database khi ứng dụng khởi động
@app.on_event("startup")
async def startup_event():
    # Tạo các bảng nếu chưa tồn tại
    init_db()

# Include các router vào ứng dụng chính
# app.include_router(base.router)
app.include_router(file_upload.router)
# app.include_router(text_to_speech.router)
app.include_router(users.router)
app.include_router(tts_facebook.router)


# @app.route("/favicon.ico")
# def favicon():
#     return "", 204


@app.get("/")
def read_root():
    return {"message": "Welcome to my FastAPI application"}
