from contextlib import asynccontextmanager
import os
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine,SQLModel,Session
from fastapi import FastAPI


# Kiểm tra môi trường để sử dụng connection string phù hợp
ENV = os.getenv("ENV", "development")
if ENV == "docker":
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:minhdang@db:5432/gold_price")
else:
    DATABASE_URL = "postgresql://postgres:minhdang@localhost:5432/gold_price"

print(f"Using database URL: {DATABASE_URL}")
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    pool_pre_ping=True,  # Kiểm tra kết nối trước khi sử dụng
    pool_size=5,  # Số lượng kết nối trong pool
    max_overflow=10  # Số lượng kết nối có thể vượt quá pool_size
)

SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind = engine)
#SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#Base = declarative_base()
def init_db():
    try:
        print("Initializing database...")
        SQLModel.metadata.create_all(engine)
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise
@asynccontextmanager
async def get_async_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


