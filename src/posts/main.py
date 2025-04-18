# src/main.py

from fastapi import FastAPI
from src.posts.router import router
import uvicorn
from src.posts.service import data_mau
from contextlib import asynccontextmanager
app = FastAPI()

if __name__ == "__main__":
    uvicorn.run("src.posts.main:app", host="localhost", port=8002, reload=True)



app.include_router(router)
# Thêm các tuyến được vào app để rễ quản lý hơn