# src/main.py

from fastapi import FastAPI

from src.posts.database import SessionLocal
from src.posts.router import router
import uvicorn
import os
# from src.posts.service import data_mau
from contextlib import asynccontextmanager
app = FastAPI()
if __name__ == "__main__":
 uvicorn.run("src.posts.main:app",host="localhost",port=8001,reload=True)
# Include router
app.include_router(router)

