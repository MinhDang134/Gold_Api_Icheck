from contextlib import asynccontextmanager

from src.posts.database import SessionLocal
from src.posts.service import data_mau


# Định nghĩa lifespan handler bằng asynccontextmanager

async def get_db():
    # Tạo một session mới khi khởi động
    db = SessionLocal()  # Tạo một session hợp lệ từ SessionLocal
    try:
        # Gọi data_mau khi khởi động
        yield db  # Trả về session để tiếp tục sử dụng trong ứng dụng
    finally:
        db.close()  # Đảm bảo đóng session khi ứng dụng tắt

