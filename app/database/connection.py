from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Thông tin kết nối MySQL
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:@127.0.0.1/db_tts"

# Tạo engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Tạo session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo base class cho model
Base = declarative_base()

# Hàm để lấy database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 