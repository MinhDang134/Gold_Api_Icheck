# src/dependencies.py

from src.posts.database import SessionLocal

from src.posts.service import data_mau
from contextlib import asynccontextmanager



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


