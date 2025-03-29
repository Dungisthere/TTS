from sqlalchemy.orm import Session
from app.database.connection import Base, engine

def init_db():
    # Tạo các bảng trong database
    Base.metadata.create_all(bind=engine) 