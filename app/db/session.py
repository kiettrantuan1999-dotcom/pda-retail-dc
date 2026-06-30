from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import DATABASE_URL

# Sprint Performance:
# - pool_pre_ping: tránh lỗi connection chết khi Railway/Supabase idle.
# - pool_recycle: tái tạo connection định kỳ để giảm lỗi stale connection.
# - pool_size/max_overflow: đủ cho 50-100 user thao tác PDA nhẹ, không mở quá nhiều connection DB.
# - pool_timeout: fail nhanh thay vì treo request quá lâu khi DB nghẽn.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    pool_timeout=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
