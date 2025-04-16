# src/main.py

from fastapi import FastAPI
from src.posts.router import router
from src.posts.service import data_mau

app = FastAPI()
@app.on_event("startup")
async def startup_event():
    await data_mau()
app.include_router(router)
# Thêm các tuyến được vào app để rễ quản lý hơn