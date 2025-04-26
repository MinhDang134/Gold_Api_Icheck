# src/main.py

from fastapi import FastAPI
from sqlmodel import SQLModel

import src.posts.models
from src.posts.database import SessionLocal, engine
from src.posts.router import router


# if __name__ == "__main__":
#  uvicorn.run("src.posts.main:app",host="localhost",port=8001,reload=True)
# # Include router
app = FastAPI()
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
@app.get("/")
def read_root():
    return {"Thông báo":"Api bắt đầu chạy"}
app.include_router(router)

